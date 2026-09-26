import json
import logging
import re
import requests
from config import Config
from ocr_service import get_image_base64_and_mime

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are HelpLens, the world's most supportive, clear, and safety-focused AI assistant for everyday household problems, appliance glitches, error codes, and DIY repairs.

Your job is to analyze the user's problem description, any OCR-extracted text, and any provided image, and return actionable, beginner-friendly, and safe step-by-step guidance.

CRITICAL INSTRUCTIONS:
1. Always put SAFETY FIRST. If water, mains electricity, gas, heavy lifting, or toxic chemicals are involved, highlight mandatory safety precautions immediately.
2. Be simple, direct, and encouraging. Avoid confusing technical jargon.
3. If an error code or model number is visible or mentioned (e.g. Bosch E18, Samsung 4C, Whirlpool F21), explain exactly what it means.
4. If symbols (like garment care labels, dashboard icons, or circuit markings) are present, decode them clearly.
5. Provide a realistic checklist of tools and materials needed so the user is prepared before starting.
6. Provide an explicit threshold of "When to Call a Professional" to protect the user from dangerous or warranty-voiding mistakes.

You MUST respond strictly in valid JSON matching this exact structure:
{
  "problem_title": "Short descriptive title of the issue",
  "category": "Appliance & Codes | Plumbing & Water | Home & DIY | Electronics & Tech | Automotive | Garden & Plants | Clothing & Labels | General",
  "severity": "low | medium | high | critical",
  "difficulty": "Beginner | Intermediate | Advanced",
  "estimated_time": "e.g. 10 - 20 minutes",
  "diagnosis": "A friendly 2-3 sentence diagnosis explaining what is happening and why.",
  "extracted_code_info": "Specific explanation of any error code, symbol, or text found, or null if none",
  "safety_warnings": [
    "Safety warning 1 (e.g., Unplug the appliance from wall power before opening any panel)",
    "Safety warning 2"
  ],
  "tools_needed": [
    "Tool or household item 1 (e.g. Phillips-head screwdriver)",
    "Tool 2 (e.g. Shallow tray or towel)"
  ],
  "materials_needed": [
    "Replacement part or consumable (e.g. Vinegar, PTFE plumber's tape, or 'None needed')"
  ],
  "steps": [
    {
      "step_number": 1,
      "title": "Clear action title",
      "instruction": "Simple, beginner-level explanation of what to do in this step.",
      "pro_tip": "Helpful insider tip or what to watch out for."
    },
    {
      "step_number": 2,
      "title": "Next action title",
      "instruction": "Detailed guidance for step 2.",
      "pro_tip": "Helpful pro tip."
    }
  ],
  "troubleshooting": [
    "What to verify if the issue persists after following the steps."
  ],
  "when_to_call_pro": [
    "Specific warning sign 1 when a certified technician or plumber is required",
    "Specific warning sign 2"
  ]
}

Only return valid JSON. Do not include extra conversational text outside the JSON.
"""

def extract_json_from_text(raw_text):
    """Clean markdown code fences and extract valid JSON."""
    if not raw_text:
        return None
    # Remove markdown ```json ... ``` wrapper if present
    cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except Exception:
        # Fallback: find outermost curly braces
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
    return None

def call_gemini_api(problem_text, category="General", urgency="Standard", image_path=None, ocr_text="", custom_api_key=None):
    """
    Call Gemini API (using REST interactions endpoint) with text and optional image input.
    Falls back gracefully to contextual mock generator if API key is absent or request fails.
    """
    api_key = custom_api_key or Config.GEMINI_API_KEY
    
    # If no API key provided, switch to Demo/Mock generator
    if not api_key:
        logger.info("No Gemini API key configured. Utilizing HelpLens Smart Demo Engine.")
        return generate_mock_guidance(problem_text, category, urgency, ocr_text, is_fallback=False)
        
    prompt_content = f"""USER PROBLEM DESCRIPTION:
{problem_text}

CATEGORY: {category}
URGENCY: {urgency}
"""
    if ocr_text:
        prompt_content += f"\nEXTRACTED TEXT / OCR FROM IMAGE:\n{ocr_text}\n"

    # Build input parts for Gemini
    inputs = [
        {"type": "text", "text": f"{SYSTEM_PROMPT}\n\n{prompt_content}"}
    ]
    
    # Add image payload if provided
    if image_path:
        try:
            b64_data, mime_type = get_image_base64_and_mime(image_path)
            inputs.append({
                "type": "image",
                "data": b64_data,
                "mime_type": mime_type
            })
        except Exception as e:
            logger.warning("Error preparing image for Gemini payload: %s", str(e))
            
    # Primary model is gemini-3.8-flash, with fallback options
    models_to_try = [Config.GEMINI_MODEL, "gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-1.5-flash"]
    
    # Deduplicate while preserving order
    seen = set()
    models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]
    
    endpoint = "https://generativelanguage.googleapis.com/v1beta/interactions"
    
    for model_name in models_to_try:
        try:
            headers = {
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            }
            body = {
                "model": model_name,
                "input": inputs
            }
            
            logger.info("Calling Gemini API interactions endpoint with model: %s", model_name)
            response = requests.post(endpoint, headers=headers, json=body, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                # Extract output_text from interactions response
                output_text = None
                
                # Check top-level or steps
                if "output_text" in data and data["output_text"]:
                    output_text = data["output_text"]
                elif "steps" in data:
                    for step in reversed(data["steps"]):
                        if step.get("type") in ("model_output", "output") and "content" in step:
                            contents = step["content"]
                            if isinstance(contents, list):
                                text_parts = [c.get("text", "") for c in contents if c.get("type") == "text"]
                                if text_parts:
                                    output_text = "".join(text_parts)
                                    break
                            elif isinstance(contents, str):
                                output_text = contents
                                break
                                
                if output_text:
                    parsed = extract_json_from_text(output_text)
                    if parsed:
                        parsed["_meta"] = {
                            "source": "gemini_api",
                            "model": model_name,
                            "is_demo_mode": False
                        }
                        return parsed
            else:
                logger.warning("Gemini interactions endpoint returned %s: %s", response.status_code, response.text[:200])
        except Exception as e:
            logger.warning("Attempt with model %s failed: %s", model_name, str(e))
            
    # Also attempt standard generateContent endpoint as secondary fallback
    for model_name in ["gemini-2.5-flash", "gemini-1.5-flash"]:
        try:
            legacy_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            parts = [{"text": f"{SYSTEM_PROMPT}\n\n{prompt_content}"}]
            if image_path:
                b64_data, mime_type = get_image_base64_and_mime(image_path)
                parts.append({
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": b64_data
                    }
                })
            
            gen_resp = requests.post(legacy_url, json={"contents": [{"parts": parts}]}, timeout=45)
            if gen_resp.status_code == 200:
                gen_data = gen_resp.json()
                cand_text = gen_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = extract_json_from_text(cand_text)
                if parsed:
                    parsed["_meta"] = {
                        "source": "gemini_generate_content",
                        "model": model_name,
                        "is_demo_mode": False
                    }
                    return parsed
        except Exception as e:
            logger.warning("Legacy API fallback attempt failed: %s", str(e))

    logger.warning("Gemini API calls exhausted or failed. Returning contextual Smart Demo response.")
    return generate_mock_guidance(problem_text, category, urgency, ocr_text, is_fallback=True)

def generate_mock_guidance(problem_text, category="General", urgency="Standard", ocr_text="", is_fallback=False):
    """
    Generates intelligent, highly realistic, contextual step-by-step assistance
    for hackathon demos and offline testing.
    """
    text_corpus = f"{problem_text} {ocr_text} {category}".lower()
    
    # Preset 1: Washing Machine / Dishwasher Drain or E18 / E15 Error Code
    if any(k in text_corpus for k in ["e18", "e15", "washing machine", "washer", "drain", "water won't drain", "pump", "f21", "4c", "oe"]):
        res = {
            "problem_title": "Washing Machine Drainage Error (Filter & Pump Blockage)",
            "category": "Appliance & Codes",
            "severity": "medium",
            "difficulty": "Beginner",
            "estimated_time": "15 - 20 minutes",
            "diagnosis": "Your washing machine stopped because water cannot discharge through the drain hose. This is typically triggered by lint, loose coins, hairpins, or small garments clogging the drain pump filter.",
            "extracted_code_info": "Detected Drain Error (equivalent to Bosch E18, Siemens E18, Whirlpool F21, or Samsung 4C/5C) indicating a drain timeout.",
            "safety_warnings": [
                "Unplug the washing machine from the electrical outlet before opening the filter chamber.",
                "Wait 30 minutes if you recently ran a high-temperature cycle to avoid scalding water.",
                "Prepare shallow trays and heavy towels — trapped water will spill when opening the filter cap."
            ],
            "tools_needed": [
                "Shallow baking tray or dustpan (to catch draining water)",
                "2-3 thick old bath towels",
                "Flashlight or phone light",
                "Needle-nose pliers (optional, for snagged debris)"
            ],
            "materials_needed": [
                "Warm water and dish soap (for cleaning filter)"
            ],
            "steps": [
                {
                    "step_number": 1,
                    "title": "Disconnect Power & Prepare Work Area",
                    "instruction": "Turn off and unplug the appliance from the mains. Place old towels and a shallow baking sheet beneath the bottom-right maintenance access door.",
                    "pro_tip": "Never skip unplugging; moisture around the lower pump assembly creates an electrical hazard."
                },
                {
                    "step_number": 2,
                    "title": "Open Maintenance Flap & Controlled Drain",
                    "instruction": "Pry open the small access flap on the bottom front corner. If your model has a small black emergency drain tube, pull it out, place the tip in a shallow tray, pull the plug, and let water drain completely before proceeding.",
                    "pro_tip": "Drain into small cups iteratively if the tray fills up, then replug the tube."
                },
                {
                    "step_number": 3,
                    "title": "Unscrew the Pump Filter",
                    "instruction": "Turn the round filter dial counter-clockwise slowly. Have a towel pressed against the bottom. Remove the filter basket completely.",
                    "pro_tip": "If the dial is stuck, don't force it with a wrench — rock it gently back and forth to loosen trapped hair."
                },
                {
                    "step_number": 4,
                    "title": "Remove Obstructions & Inspect Impeller",
                    "instruction": "Clean all lint, coins, and hair from the filter chamber. Shine your flashlight inside the cavity and spin the small plastic fan impeller with your finger to confirm it turns freely.",
                    "pro_tip": "Even a tiny hairpin lodged behind the impeller blades will prevent the pump from spinning."
                },
                {
                    "step_number": 5,
                    "title": "Reinstall, Seal Tightly, and Test Cycle",
                    "instruction": "Wash the filter with warm water, insert it straight, and screw clockwise until firmly locked. Close the access flap, restore power, and run a short rinse/spin cycle with an empty drum.",
                    "pro_tip": "If the error code does not clear instantly, turn the selector dial to Off for 10 seconds to reset the computer."
                }
            ],
            "troubleshooting": [
                "If the drum still won't drain, check if the external drain hose behind the machine is kinked or clogged at the sink waste pipe connector.",
                "Ensure the sink spigot is drilled open if this was a recently installed drain connection."
            ],
            "when_to_call_pro": [
                "The pump impeller doesn't turn even when completely free of debris, or makes loud grinding screech noises (burned pump motor).",
                "Water continues leaking from inside the machine housing even with the filter tight."
            ]
        }
    
    # Preset 2: Leaky Faucet / Dripping Tap / Running Toilet
    elif any(k in text_corpus for k in ["faucet", "tap", "leak", "drip", "toilet", "running water", "plumbing", "pipe", "sink"]):
        res = {
            "problem_title": "Dripping Faucet / Leaky Valve Fix",
            "category": "Plumbing & Water",
            "severity": "medium",
            "difficulty": "Beginner",
            "estimated_time": "20 - 30 minutes",
            "diagnosis": "Continuous dripping or weeping from a faucet is usually caused by a degraded silicone O-ring, mineral scale deposits, or a worn ceramic disc cartridge inside the faucet handle.",
            "extracted_code_info": "Household Plumbing Fixture Analysis: Standard single-lever mixer or compression valve.",
            "safety_warnings": [
                "CRITICAL: Shut off the water supply isolation valves beneath the sink before loosening any fixture nuts.",
                "Cover the sink drain with a rag or stopper so screws and small washers cannot fall down the drain pipe."
            ],
            "tools_needed": [
                "Adjustable wrench or channel-lock pliers",
                "Phillips and flat-head screwdrivers",
                "Allen / hex key set (usually 2.5mm or 3mm)",
                "Clean rag or drain plug"
            ],
            "materials_needed": [
                "Replacement cartridge or washer set (match existing size)",
                "Plumber's silicone grease",
                "White vinegar (to dissolve mineral scale)"
            ],
            "steps": [
                {
                    "step_number": 1,
                    "title": "Shut Off Water Supply & Relieve Pressure",
                    "instruction": "Look under the sink for the oval shut-off valves. Turn both clockwise until tight. Open the faucet to full blast to bleed off remaining water pressure.",
                    "pro_tip": "If under-sink valves are stiff, shut off your home's main water supply valve outside or in the basement."
                },
                {
                    "step_number": 2,
                    "title": "Remove the Handle Cap and Retaining Screw",
                    "instruction": "Pry off the small hot/cold decorative plastic badge on the handle using a thin blade. Use your hex key or screwdriver to remove the hidden screw underneath, then lift the handle off.",
                    "pro_tip": "If the handle feels seized from calcium deposits, soak a vinegar-dampened cloth around the base for 15 minutes."
                },
                {
                    "step_number": 3,
                    "title": "Unscrew the Decorative Collar & Retaining Nut",
                    "instruction": "Unscrew the domed chrome collar by hand. Use an adjustable wrench to loosen the large brass retaining nut holding the internal cartridge in place.",
                    "pro_tip": "Wrap a layer of electrical tape around your wrench jaws to avoid scratching delicate chrome plating."
                },
                {
                    "step_number": 4,
                    "title": "Extract and Inspect the Cartridge",
                    "instruction": "Pull the cartridge straight up. Check the bottom rubber O-rings and ceramic discs for tears, calcification, or debris. Soak the parts in warm white vinegar to dissolve limescale.",
                    "pro_tip": "Take a photo of the cartridge orientation so you reinstall it with the alignment tabs matching."
                },
                {
                    "step_number": 5,
                    "title": "Reassemble and Test for Leaks",
                    "instruction": "Insert the cleaned or replacement cartridge into the slots, tighten the retaining nut firmly (do not over-torque), replace the handle, and slowly restore the water valve.",
                    "pro_tip": "Turn the water supply valve on slowly to avoid pressure surges that can dislodge pipe sediment."
                }
            ],
            "troubleshooting": [
                "If dripping persists after a new cartridge, inspect the brass valve seat inside the faucet body for scratches or pitting.",
                "Ensure aerator at the nozzle is unscrewed and cleaned of dislodged pipe rust."
            ],
            "when_to_call_pro": [
                "The under-sink isolation valve itself is leaking or won't shut off completely.",
                "The copper supply lines show deep corrosion or solder joint hairline fractures."
            ]
        }

    # Preset 3: Wi-Fi Router / Internet Connection / Tech Glitch
    elif any(k in text_corpus for k in ["router", "wifi", "wi-fi", "internet", "red light", "los", "modem", "connection", "network", "no internet"]):
        res = {
            "problem_title": "Wi-Fi Router Offline / Red Status Light Diagnosis",
            "category": "Electronics & Tech",
            "severity": "medium",
            "difficulty": "Beginner",
            "estimated_time": "5 - 10 minutes",
            "diagnosis": "A solid or flashing red/orange light on your Wi-Fi router (often labeled 'Internet', 'WAN', or 'LOS') indicates that while local Wi-Fi broadcasting is active, the router has lost handshake communication with the upstream ISP signal.",
            "extracted_code_info": "Network Hardware Indicator: Optical LOS (Loss of Signal) or WAN IP handshake timeout.",
            "safety_warnings": [
                "Do NOT press the recessed 'Factory Reset' pinhole unless instructed by your ISP, as this will wipe your custom Wi-Fi network name and password.",
                "Keep liquid and cleaners far away from ventilation grilles."
            ],
            "tools_needed": [
                "Smartphone (using cellular data to check ISP status)",
                "Flashlight to inspect cables behind the unit"
            ],
            "materials_needed": [
                "None needed"
            ],
            "steps": [
                {
                    "step_number": 1,
                    "title": "Inspect Cable Seating and Fiber Jack",
                    "instruction": "Check the back of the router. Ensure the blue/yellow Ethernet cable (WAN port) or green optical fiber cord is firmly clicked into position. Make sure no cables are pinched behind furniture.",
                    "pro_tip": "Never sharply bend a thin fiber optic cable; the glass core can fracture internally."
                },
                {
                    "step_number": 2,
                    "title": "Perform a Clean 30-Second Power Cycle",
                    "instruction": "Unplug the black power adapter cord from the back of the router (and separate modem/ONT if present). Wait a full 30 seconds for the internal capacitors to discharge completely, then plug it back in.",
                    "pro_tip": "Do not just press the power toggle on and off immediately; the waiting period clears stale DHCP network cache."
                },
                {
                    "step_number": 3,
                    "title": "Observe the LED Boot Sequence",
                    "instruction": "Wait 3 to 4 minutes. Watch the status lights: Power should turn solid green/white, followed by 2.4GHz/5GHz WLAN, and finally the Globe/Internet light should transition to green/white.",
                    "pro_tip": "If the 'LOS' (Loss of Signal) light flashes red on a fiber terminal, the fiber line outside is broken and requires ISP dispatch."
                },
                {
                    "step_number": 4,
                    "title": "Verify Device DNS & Reconnect",
                    "instruction": "On your phone or laptop, toggle Wi-Fi off and on, connect to your home network, and attempt visiting an un-cached site such as example.com or fast.com.",
                    "pro_tip": "If one device fails while others work, 'Forget Network' on that single device and enter your password again."
                }
            ],
            "troubleshooting": [
                "Check your mobile carrier data to see if your internet service provider has reported a regional area fiber outage.",
                "Log into router admin portal (usually 192.168.1.1 or 192.168.0.1) to view the WAN connection error log."
            ],
            "when_to_call_pro": [
                "The optical fiber cable is visibly kinked or snapped.",
                "All lights remain dark despite testing different electrical wall outlets (blown power supply)."
            ]
        }

    # Preset 4: Yellowing Houseplant Leaves / Plant Care
    elif any(k in text_corpus for k in ["plant", "leaves", "yellow", "foliage", "watering", "monstera", "pothos", "soil", "succulent", "drooping"]):
        res = {
            "problem_title": "Houseplant Chlorosis & Yellowing Leaves Diagnosis",
            "category": "Garden & Plants",
            "severity": "low",
            "difficulty": "Beginner",
            "estimated_time": "10 minutes",
            "diagnosis": "Yellowing leaves (chlorosis) are most commonly caused by moisture stress — specifically overwatering leading to root oxygen starvation — or low ambient light. Older lower leaves yellowing naturally can also indicate normal foliage turnover.",
            "extracted_code_info": "Botanical Health Inspection: Common indoor foliage showing signs of early moisture imbalance.",
            "safety_warnings": [
                "Keep plant pruning shears away from children.",
                "Wash hands after pruning if dealing with sap-producing plants like Ficus or Euphorbia, which can cause skin irritation."
            ],
            "tools_needed": [
                "Clean pruning shears or sharp kitchen scissors",
                "Wooden chopstick or moisture meter",
                "Rubbing alcohol (to sterilize blades)"
            ],
            "materials_needed": [
                "Fresh well-draining potting mix (perlite/peat) if repotting is required"
            ],
            "steps": [
                {
                    "step_number": 1,
                    "title": "Perform the Wooden Chopstick Soil Moisture Test",
                    "instruction": "Insert a plain wooden chopstick 2 inches deep into the soil near the center. Pull it out. If it comes out dark and damp with soil clinging to it, the root zone is saturated. If dry and clean, the plant is dehydrated.",
                    "pro_tip": "The surface soil often dries out while the bottom 4 inches remain soaked in non-draining pots."
                },
                {
                    "step_number": 2,
                    "title": "Check Drainage and Drain Catch Saucer",
                    "instruction": "Lift the inner nursery pot out of the decorative outer ceramic planter. Ensure water is not pooled at the bottom of the outer pot. Empty any standing saucer water immediately.",
                    "pro_tip": "Roots sitting in standing water suffocate within 48 hours, leading to anaerobic root rot."
                },
                {
                    "step_number": 3,
                    "title": "Prune Severely Yellowed Leaves",
                    "instruction": "Wipe scissors with rubbing alcohol. Snip off leaves that are greater than 50% yellow or brown near the base of the petiole stem to redirect plant energy to healthy new growth.",
                    "pro_tip": "Leaves that are fully yellow will never photosynthesize again; removing them prevents mold."
                },
                {
                    "step_number": 4,
                    "title": "Optimize Sunlight Exposure & Water Cadence",
                    "instruction": "Move the plant 2-3 feet closer to an east- or south-facing window with bright, indirect light. Do not water again until the top 2 inches of soil feel dry to the touch.",
                    "pro_tip": "In winter months, indoor plants drink half as much water as during the summer growing season."
                }
            ],
            "troubleshooting": [
                "Inspect the undersides of leaves with your flashlight for fine webbing or tiny speckled dust, which indicates spider mites.",
                "If brown tips are crispy, room humidity may be below 30% — group plants together or use a humidifier."
            ],
            "when_to_call_pro": [
                "The soil smells like sulfur/rotting eggs and plant stems feel mushy at the soil line (advanced root rot needing root trimming and fungicide)."
            ]
        }

    # Preset 5: Car Dashboard Warning Light / Check Engine / Tire TPMS
    elif any(k in text_corpus for k in ["car", "dashboard", "engine light", "tire", "tpms", "battery light", "vehicle", "oil light", "brake light"]):
        res = {
            "problem_title": "Vehicle Dashboard Warning Indicator Assessment",
            "category": "Automotive",
            "severity": "high",
            "difficulty": "Beginner",
            "estimated_time": "10 - 15 minutes",
            "diagnosis": "Automotive dashboard indicators communicate system alerts. Yellow/Amber icons mean 'service or inspect soon', while Red icons require immediate pull-over safety action to prevent catastrophic engine or brake failure.",
            "extracted_code_info": "Automotive Telemetry Indicator: Check Engine (OBD-II), TPMS (Low Tire Pressure), or Alternator charging circuit.",
            "safety_warnings": [
                "CRITICAL: If the Check Engine Light is FLASHING (blinking), pull over immediately; an active cylinder misfire is dumping raw fuel into the catalytic converter.",
                "Never open the radiator or coolant expansion tank cap while the engine is hot.",
                "Park on level ground with the emergency handbrake engaged before inspecting under the hood."
            ],
            "tools_needed": [
                "Tire pressure gauge",
                "Pocket OBD-II Bluetooth scanner (optional)",
                "Flashlight"
            ],
            "materials_needed": [
                "Appropriate engine oil grade or windshield wiper fluid if topping up"
            ],
            "steps": [
                {
                    "step_number": 1,
                    "title": "Identify Indicator Color and Pattern",
                    "instruction": "Note if the icon is Amber (warning) or Red (danger). Confirm whether the light is steady or flashing. If red and accompanied by a chime, safely pull to the road shoulder.",
                    "pro_tip": "A steady amber Check Engine Light is safe to drive for short distances to reach an auto parts store or garage."
                },
                {
                    "step_number": 2,
                    "title": "Check the Gas Cap Seal (Most Common Amber Trigger)",
                    "instruction": "Turn off the ignition. Unscrew your fuel cap, inspect the rubber gasket for cracks, screw it back on until it clicks 3 times. An evaporative emission (EVAP) leak will clear the light after 1-2 drive cycles.",
                    "pro_tip": "A loose gas cap triggers code P0455/P0457 on almost all modern vehicles."
                },
                {
                    "step_number": 3,
                    "title": "Check Tire Pressures (If Horseshoe Icon with '!')",
                    "instruction": "Open the driver's door jamb to view the manufacturer's recommended PSI sticker (usually 32-35 PSI). Use a pressure gauge on each valve stem while tires are cold, and inflate at a local station.",
                    "pro_tip": "Sudden temperature drops in autumn reduce tire pressure by ~1 PSI for every 10°F drop."
                },
                {
                    "step_number": 4,
                    "title": "Read Diagnostic Trouble Code (DTC)",
                    "instruction": "Plug an OBD-II scanner into the 16-pin port under the steering wheel dashboard, turn ignition to ON, and read the 5-character fault code (e.g. P0300, P0420, P0171).",
                    "pro_tip": "Most auto parts stores (like AutoZone, O'Reilly) will read your OBD-II codes for free in the parking lot."
                }
            ],
            "troubleshooting": [
                "If the battery light is illuminated while driving, the alternator is failing; minimize electrical loads (turn off A/C and stereo) and drive to the nearest shop.",
                "Check fluid levels (oil dipstick, coolant level) in the engine bay."
            ],
            "when_to_call_pro": [
                "Flashing check engine light accompanied by severe engine shaking or loss of acceleration.",
                "Red oil pressure can icon lights up (engine lacks oil pressure; turn off engine instantly)."
            ]
        }

    # Preset 6: Clothing Wash Care Label / Iron / Dry Clean Symbols
    elif any(k in text_corpus for k in ["garment", "clothing", "wash", "care label", "tag", "iron", "dry clean", "bleach", "tumble dry", "fabric"]):
        res = {
            "problem_title": "Garment Care Label Symbols Decoded",
            "category": "Clothing & Labels",
            "severity": "low",
            "difficulty": "Beginner",
            "estimated_time": "5 minutes",
            "diagnosis": "Garment care labels follow universal ISO/ASTM textile care standards across 5 key categories: Washing (washtub), Bleaching (triangle), Drying (square), Ironing (iron), and Professional Cleaning (circle).",
            "extracted_code_info": "Textile Care Standard ISO 3758: Universal symbols decoded.",
            "safety_warnings": [
                "Never use chlorine bleach on garments marked with a crossed-out triangle.",
                "Do not tumble-dry wool, silk, or garments marked with a crossed-out circle inside a square; shrinking is permanent."
            ],
            "tools_needed": [
                "Mesh laundry wash bag (for delicates)",
                "Measuring cup for detergent"
            ],
            "materials_needed": [
                "Mild liquid detergent or wool/silk wash",
                "Color-safe oxygen bleach (if stain treatment needed)"
            ],
            "steps": [
                {
                    "step_number": 1,
                    "title": "Decode the Washtub (Washing Temperature)",
                    "instruction": "The open tub indicates water wash. If dots are inside: 1 dot = Cold (30°C/85°F), 2 dots = Warm (40°C/105°F), 3 dots = Hot (50°C/120°F). If a line is beneath the tub, use the Gentle/Perm-Press cycle.",
                    "pro_tip": "A hand inside the washtub means strictly hand-wash only; do not place in a machine drum."
                },
                {
                    "step_number": 2,
                    "title": "Decode the Triangle (Bleach Instructions)",
                    "instruction": "An empty triangle means any bleach is safe. A triangle with diagonal stripes means non-chlorine (oxygen) bleach only. An 'X' through the triangle means NO bleach.",
                    "pro_tip": "Oxygen bleach (sodium percarbonate) is fabric-safe and removes tough collar grime without yellowing whites."
                },
                {
                    "step_number": 3,
                    "title": "Decode the Square (Drying Cycle)",
                    "instruction": "A circle inside a square denotes machine tumble dry. 1 dot = Low heat, 2 dots = Medium heat, 3 dots = High heat. A horizontal line inside a square means 'Dry Flat' (essential for heavy knit sweaters).",
                    "pro_tip": "Hanging wet knits on clothes hangers will stretch out the shoulders permanently; always dry flat on a towel."
                },
                {
                    "step_number": 4,
                    "title": "Decode the Iron (Heat Level)",
                    "instruction": "1 dot on iron symbol = Low heat (110°C, nylon/acrylic), 2 dots = Medium (150°C, polyester/wool), 3 dots = High heat (200°C, cotton/linen). An iron with steam lines crossed out means dry iron only.",
                    "pro_tip": "Place a thin cotton tea towel between the iron and dark garments to prevent shiny iron burns."
                }
            ],
            "troubleshooting": [
                "A circle with an 'X' indicates Do Not Dry Clean. A plain circle with a letter (e.g. 'P' or 'F') specifies dry cleaning solvent type for commercial cleaners.",
                "For delicate lace or screen-printed shirts, always turn inside out before laundering."
            ],
            "when_to_call_pro": [
                "Garments labeled 'Dry Clean Only' made of structured suit wool, silk taffeta, or genuine leather."
            ]
        }

    # Default / General Household & DIY Problem Handler
    else:
        title = problem_text.split("\n")[0][:60] if problem_text else "Everyday Problem Assessment"
        res = {
            "problem_title": f"HelpLens Guide: {title}",
            "category": category if category != "All" else "Home & DIY",
            "severity": "low" if urgency == "Beginner / Low Tools" else "medium",
            "difficulty": "Beginner",
            "estimated_time": "15 - 25 minutes",
            "diagnosis": f"Based on your input ('{problem_text[:120]}...'), HelpLens has evaluated the typical mechanical and structural causes. Most common occurrences are resolved with basic adjustments, tightening, or cleaning.",
            "extracted_code_info": ocr_text if ocr_text else "Visual observation and symptom pattern matched.",
            "safety_warnings": [
                "Ensure adequate room ventilation and wear safety glasses if chipping, scraping, or spraying lubricants.",
                "If dealing with mechanical moving parts or electrical connections, ensure all power switches are off."
            ],
            "tools_needed": [
                "Standard screwdriver set (Flathead & Phillips)",
                "Microfiber cloth or clean rag",
                "Flashlight or phone light",
                "Adjustable pliers"
            ],
            "materials_needed": [
                "Multi-purpose silicone spray or WD-40 Specialist",
                "Mild household cleaning solution"
            ],
            "steps": [
                {
                    "step_number": 1,
                    "title": "Isolate the Area & Clear Surrounding Space",
                    "instruction": "Clear any clutter around the item so you have comfortable access and good lighting. Inspect the perimeter for loose screws, misalignment, or signs of wear.",
                    "pro_tip": "Take a quick smartphone photo of the assembly before disassembling so you remember the exact screw order."
                },
                {
                    "step_number": 2,
                    "title": "Perform Initial Cleaning and Debris Inspection",
                    "instruction": "Wipe away grime, built-up dust, or dried residue using a damp microfiber cloth. Often friction or jamming is simply caused by trapped grit.",
                    "pro_tip": "Avoid spraying liquid cleaners directly into electronic seams; spray onto the cloth first."
                },
                {
                    "step_number": 3,
                    "title": "Check Fasteners and Align Structural Points",
                    "instruction": "Gently tighten any loose mounting bolts or screws. Ensure you do not over-tighten into plastic or soft composite wood, which can strip the threads.",
                    "pro_tip": "If a screw hole in wood is stripped, insert a wooden toothpick dipped in wood glue, snap flush, and re-drive the screw."
                },
                {
                    "step_number": 4,
                    "title": "Apply Targeted Lubrication or Alignment Adjustment",
                    "instruction": "Apply a drop of silicone lubricant to pivot hinges or glide tracks. Wipe away any excess immediately to prevent attracting new dust.",
                    "pro_tip": "Use dry graphite lubricant rather than wet oil on door locks and keyholes so dust doesn't gum up internal pins."
                },
                {
                    "step_number": 5,
                    "title": "Test Operation and Verify Stability",
                    "instruction": "Cycle the mechanism through its full range of motion 3 times. Verify smooth operation without binding, squeaking, or wobbling.",
                    "pro_tip": "If intermittent issues recur, note whether ambient temperature or humidity triggers the friction."
                }
            ],
            "troubleshooting": [
                "If the part continues to stick, inspect for warped metal or swollen composite wood.",
                "Ensure all weight-bearing brackets are plumb and level."
            ],
            "when_to_call_pro": [
                "There are signs of structural sagging, deep cracks in load-bearing members, or burning electrical odors.",
                "The repair involves internal high-voltage components (capacitors, transformers)."
            ]
        }

    res["_meta"] = {
        "source": "smart_demo_engine",
        "model": "helplens-heuristics-v1",
        "is_demo_mode": True,
        "is_fallback": is_fallback
    }
    return res
