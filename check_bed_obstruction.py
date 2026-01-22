from ollama import Client
import requests
import os
import json

IMAGE_PATH = os.path.expanduser("~/printer_data/config/bed_images/")

class CheckBedObstruction:
    def __init__(self, config):
        self.register_class_vars(config)

        # Prompt override in case user wants to tweak the performance.
        self.prompt = f'''
            System Prompt: You are an expert 3D printing quality control engineer.
            Your sole task is to determine if the 3D printer bed is clear for a new print.
            An "obstruction" includes any printed objects, loose plastic (spaghetti),
            tools, or debris left on the print surface. If you do not see the bed in one image,
            only consider any images where the bed is visible, instead.{self.prompt_extension}

            {(f"The first {len(self.camera_snapshot_urls)} image(s) are the current live images of the bed."
              f"The last {len(self.reference_images)} image(s) depict examples of the bed when clear. Please take"
              f"the clear images into consideration when making your determination.")
            if len(self.reference_images) else ""}

            User Prompt: Analyze the provided image of the 3D printer bed.
            Follow these steps: Identify the print bed surface. Search for any objects,
            or tools on the bed that may damage the printhead upon homing. Ignore the toolhead or minor objects 
            such as loose filament that do not pose a risk of damage. 

            Return only a json string with the keys, 'clear' and 'reason.' 
            If the bed is clear, 'clear' should be just '1'. If the bed is not clear, 'clear' should be just '0'.
            If the bed is not clear, provide a detailed reason in the 'reason' key with location and shape of the
            object. 
            '''

        self.printer.add_object('CheckBedObstruction', self)
        
        self.register_commands()
    
    # --------------------- CLASS FUNCTIONS ---------------------
    def register_class_vars(self, config):
        self.printer = config.get_printer()
        self.bed_clear = 1  # Default to the bed being clear.
        self.gcode = self.printer.lookup_object('gcode')

        # Read API key from config
        self.api_key = config.get('api_key', None)
        if not self.api_key:
            raise config.error("check_bed_obstruction: api_key is required!")

        # List of comma separated camera snapshot urls for the ai to receive images from.
        self.camera_snapshot_urls = config.get(
            'camera_snapshot_urls',
            None
        ).split(',')
        if not self.camera_snapshot_urls:
            raise config.error("check_bed_obstruction: camera_snapshot_url is required!")

        # The chamber led command name so that it can be lit up before running the script.
        self.chamber_led_command = config.get(
            'chamber_led_command',
            None
        )

        # The ai model to use.
        # List of models: https://ollama.com/search?c=vision&c=cloud
        self.model = config.get(
            'model',
            'qwen3-vl:235b-instruct-cloud'
        )

        # An extension to the prompt for more flexibility. For ex. "My print bed is black. The toolhead has a
        # red cpap duct that is fed with a black umbilical cpap tube.
        self.prompt_extension = config.get(
            'prompt_extension',
            ''
        )

        # List of clear reference images.
        self.reference_images = [f"{IMAGE_PATH}{i}" for i in os.listdir(IMAGE_PATH)]

        # Initialize Ollama client.
        self.client = Client(host='https://ollama.com', headers={'Authorization': f'Bearer {self.api_key}'})

    def register_commands(self):
        '''
        This function registers GCODE commands with the printer firmware.
        '''
        
        # Register the public command
        self.gcode.register_command(
            'CHECK_BED_OBSTRUCTION',
            self.cmd_CHECK_BED_OBSTRUCTION,
            "Initiates the bed obstruction check sequence."
        )

        # Register the internal command
        self.gcode.register_command(
            '_PERFORM_BED_CHECK',
            self.cmd_PERFORM_BED_CHECK,
            "Internal worker for bed check."
        )

        # Register the take clear image command
        self.gcode.register_command(
            'TAKE_CLEAR_OBSTRUCTION_IMAGES',
            self.cmd_TAKE_REFERENCE_IMAGES,
            "Takes a picture of the bed when it is clear of obstructions for the AI."
        )
    
    
    # --------------------- GCODE MACROS --------------------- 
    def cmd_CHECK_BED_OBSTRUCTION(self, gcmd):
        """
        This function sets up the command queue for the plugin.
        """

        # Turn on lights (if configured)
        if self.chamber_led_command:
            self.gcode.run_script_from_command(
                self.chamber_led_command
            )

        # Wait 2 seconds for camera to catch up
        self.gcode.run_script_from_command("G4 P2000")

        # Run the AI script
        self.gcode.run_script_from_command("_PERFORM_BED_CHECK")

    def cmd_PERFORM_BED_CHECK(self, gcmd):
        """
        This function runs the ai workload to check if the bed is obstructed.
        """

        try:
            gcmd.respond_info("Capturing images and checking for obstructions...")

            # Download the live images
            images = []
            for snapshot in self.camera_snapshot_urls:
                response = requests.get(snapshot, timeout=20)
                if response.status_code != 200:
                    gcmd.error("Failed to download camera image")
                    return
                images.append(response.content)

            # Add clear bed images to images list for upload
            for file in self.reference_images:
                images.append(file)

            # Send to Ollama Cloud and get response
            res = self.client.chat(model=self.model, 
                                   messages=[{'role': 'user','content': (self.prompt),'images': images}]
            )

            # Convert response to json format
            res = parse_json(res)

            # Get status from response
            try:
                bed_clear_status = int(res['clear'])
            except ValueError:
                gcmd.error(f"AI returned invalid response: {res.message.content}")
                return
            self.bed_clear = bed_clear_status

            # Evaluate response
            if self.bed_clear == 0:
                raise gcmd.error(f"Bed obstructed by object! Reason: {res['reason']}")
            else:
                gcmd.respond_info("Bed is clear.")

        except Exception as e:
            raise gcmd.error(f"CHECK_BED_OBSTRUCTION Error: {e}")

    def cmd_TAKE_REFERENCE_IMAGES(self, gcmd):
        '''
        This gcode command takes clear reference images for the AI to consider.
        '''
        
        try:
            # Create image directory if it does not exist
            if not os.path.exists(IMAGE_PATH):
                gcmd.respond_info(f"{IMAGE_PATH} does not exist. Creating...")
                os.makedirs(IMAGE_PATH, exist_ok=True)
                gcmd.respond_info(f"Created: {IMAGE_PATH}")
            else:
                gcmd.respond_info(f"Found existing directory: {IMAGE_PATH}")

                # Delete old images in directory
                for filename in os.listdir(IMAGE_PATH):
                    file_path = os.path.join(IMAGE_PATH, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

            gcmd.respond_info(f"Downloading images from snapshot urls...")
            for index, snapshot in enumerate(self.camera_snapshot_urls):
                response = requests.get(snapshot, stream=True, timeout=20)
                response.raise_for_status()

                image = f"{IMAGE_PATH}image{index}.jpg"
                with open(image, 'wb') as f:
                    gcmd.respond_info(f"Downloading {image}...")
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                    gcmd.respond_info(f"Done downloading {image}!")

            gcmd.respond_info(f"Done downloading images!")
        except Exception as e:
            gcmd.error(f"Failed to download bed images. {e}")


# --------------------- STATIC FUNCTIONS --------------------- 
def parse_json(res):
    '''
    This function parses the json string returned by the AI.
    '''

    raw_content = str(res.message.content)
    if "```" in raw_content:
        json_str = raw_content.split("```")[1].replace("json\n", "").strip()
    else:
        json_str = raw_content.strip()
    res = json.loads(json_str)
    
    return res

def load_config(config):
    return CheckBedObstruction(config)
