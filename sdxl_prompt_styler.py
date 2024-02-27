import json
import os

def read_json_file(file_path):
    """
    Reads a JSON file's content and returns it.
    Ensures content matches the expected format.
    """
    if not os.access(file_path, os.R_OK):
        print(f"Warning: No read permissions for file {file_path}")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = json.load(file)
            # Check if the content matches the expected format.
            if not all(['name' in item and 'prompt' in item and 'negative_prompt' in item for item in content]):
                print(f"Warning: Invalid content in file {file_path}")
                return None
            return content
    except Exception as e:
        print(f"An error occurred while reading {file_path}: {str(e)}")
        return None


def read_sdxl_styles(json_data):
    """
    Returns style names from the provided JSON data.
    """
    if not isinstance(json_data, list):
        print("Error: input data must be a list")
        return []

    return [item['name'] for item in json_data if isinstance(item, dict) and 'name' in item]

def get_all_json_files(directory):
    """
    Returns all JSON files from the specified directory.
    """
    return [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.json') and os.path.isfile(os.path.join(directory, file))]


def load_styles_from_directory(directory):
    """
    Loads styles from all JSON files in the directory.
    Renames duplicate style names by appending a suffix.
    """
    json_files = get_all_json_files(directory)
    combined_data = []
    seen = set()

    for json_file in json_files:
        json_data = read_json_file(json_file)
        if json_data:
            for item in json_data:
                original_style = item['name']
                style = original_style
                suffix = 1
                while style in seen:
                    style = f"{original_style}_{suffix}"
                    suffix += 1
                item['name'] = style
                seen.add(style)
                combined_data.append(item)

    unique_style_names = [item['name'] for item in combined_data if isinstance(item, dict) and 'name' in item]
    
    return combined_data, unique_style_names


def validate_json_data(json_data):
    """
    Validates the structure of the JSON data.
    """
    if not isinstance(json_data, list):
        return False
    for template in json_data:
        if 'name' not in template or 'prompt' not in template:
            return False
    return True

def find_template_by_name(json_data, template_name):
    """
    Returns a template from the JSON data by name or None if not found.
    """
    for template in json_data:
        if template['name'] == template_name:
            return template
    return None

def split_template_advanced(template: str) -> tuple:
    """
    Splits a template into two parts based on a specific pattern.
    """
    if " . " in template:
        template_prompt_g, template_prompt_l = template.split(" . ", 1)
        template_prompt_g = template_prompt_g.strip()
        template_prompt_l = template_prompt_l.strip()
    else:
        template_prompt_g = template
        template_prompt_l = ""

    return template_prompt_g, template_prompt_l

def replace_prompts_in_template(template, positive_prompt, negative_prompt):
    """
    Replace the placeholders in a given template with the provided prompts.
    
    Args:
    - template (dict): The template containing prompt placeholders.
    - positive_prompt (str): The positive prompt to replace '{prompt}' in the template.
    - negative_prompt (str): The negative prompt to be combined with any existing negative prompt in the template.

    Returns:
    - tuple: A tuple containing the replaced positive and negative prompts.
    """
    positive_result = template['prompt'].replace('{prompt}', positive_prompt)

    json_negative_prompt = template.get('negative_prompt', "")
    negative_result = f"{json_negative_prompt}, {negative_prompt}" if json_negative_prompt and negative_prompt else json_negative_prompt or negative_prompt

    return positive_result, negative_result

def replace_prompts_in_template_advanced(template, positive_prompt_g, positive_prompt_l, negative_prompt, negative_prompt_to, copy_to_l):
    """
    Replace the placeholders in a given template with the provided prompts and split them accordingly.
    
    Args:
    - template (dict): The template containing prompt placeholders.
    - positive_prompt_g (str): The main positive prompt to replace '{prompt}' in the template.
    - positive_prompt_l (str): The auxiliary positive prompt to be combined in a specific manner.
    - negative_prompt (str): The negative prompt to be combined with any existing negative prompt in the template.
    - negative_prompt_to (str): The negative prompt destination {Both, G only, L only}.
    - copy_to_l (bool): Copy the G positive prompt to L.

    Returns:
    - tuple: A tuple containing the replaced main positive, auxiliary positive, combined positive,  main negative, auxiliary negative, and negative prompts.
    """
    template_prompt_g, template_prompt_l_template = split_template_advanced(template['prompt'])

    text_g_positive = template_prompt_g.replace("{prompt}", positive_prompt_g)

    text_l_positive = f"{template_prompt_l_template.replace('{prompt}', positive_prompt_g)}, {positive_prompt_l}" if template_prompt_l_template and positive_prompt_l else template_prompt_l_template.replace('{prompt}', positive_prompt_g) or positive_prompt_l

    if copy_to_l and positive_prompt_g and "{prompt}" not in template_prompt_l_template:
        token_positive_g = list(map(lambda x: x.strip(), text_g_positive.split(",")))
        token_positive_l = list(map(lambda x: x.strip(), text_l_positive.split(",")))

        # deduplicate common prompt parts
        for token_g in token_positive_g:
            if token_g in token_positive_l:
                token_positive_l.remove(token_g)

        token_positive_g.extend(token_positive_l)

        text_l_positive = ", ".join(token_positive_g)

    text_positive = f"{text_g_positive} . {text_l_positive}" if text_l_positive else text_g_positive

    json_negative_prompt = template.get('negative_prompt', "")
    text_negative = f"{json_negative_prompt}, {negative_prompt}" if json_negative_prompt and negative_prompt else json_negative_prompt or negative_prompt

    text_g_negative = ""
    if negative_prompt_to in ("Both", "G only"):
        text_g_negative = text_negative

    text_l_negative = ""
    if negative_prompt_to in ("Both", "L only"):
        text_l_negative = text_negative

    return text_g_positive, text_l_positive, text_positive, text_g_negative, text_l_negative, text_negative

def read_sdxl_templates_replace_and_combine(json_data, template_name, positive_prompt, negative_prompt):
    """
    Find a specific template by its name, then replace and combine its placeholders with the provided prompts.
    
    Args:
    - json_data (list): The list of templates.
    - template_name (str): The name of the desired template.
    - positive_prompt (str): The positive prompt to replace placeholders.
    - negative_prompt (str): The negative prompt to be combined.

    Returns:
    - tuple: A tuple containing the replaced and combined positive and negative prompts.
    """
    if not validate_json_data(json_data):
        return positive_prompt, negative_prompt

    template = find_template_by_name(json_data, template_name)

    if template:
        return replace_prompts_in_template(template, positive_prompt, negative_prompt)
    else:
        return positive_prompt, negative_prompt
    
def read_sdxl_templates_replace_and_combine_advanced(json_data, template_name, positive_prompt_g, positive_prompt_l, negative_prompt, negative_prompt_to, copy_to_l):
    """
    Find a specific template by its name, then replace and combine its placeholders with the provided prompts in an advanced manner.
    
    Args:
    - json_data (list): The list of templates.
    - template_name (str): The name of the desired template.
    - positive_prompt_g (str): The main positive prompt.
    - positive_prompt_l (str): The auxiliary positive prompt.
    - negative_prompt (str): The negative prompt to be combined.
    - negative_prompt_to (str): The negative prompt destination {Both, G only, L only}.
    - copy_to_l (bool): Copy the G positive prompt to L.

    Returns:
    - tuple: A tuple containing the replaced and combined main positive, auxiliary positive, combined positive, main negative, auxiliary negative, and negative prompts.
    """
    if not validate_json_data(json_data):
        return positive_prompt_g, positive_prompt_l, f"{positive_prompt_g} . {positive_prompt_l}", negative_prompt, negative_prompt, negative_prompt

    template = find_template_by_name(json_data, template_name)

    if template:
        return replace_prompts_in_template_advanced(template, positive_prompt_g, positive_prompt_l, negative_prompt, negative_prompt_to, copy_to_l)
    else:
        return positive_prompt_g, positive_prompt_l, f"{positive_prompt_g} . {positive_prompt_l}", negative_prompt, negative_prompt, negative_prompt


class SDXLPromptStyler:

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(self):
        current_directory = os.path.dirname(os.path.realpath(__file__))
        self.json_data, styles = load_styles_from_directory(current_directory)
        
        return {
            "required": {
                "text_positive": ("STRING", {"default": "", "multiline": True}),
                "text_negative": ("STRING", {"default": "", "multiline": True}),
                "style": ((styles), ),
                "log_prompt": ("BOOLEAN", {"default": True, "label_on": "yes", "label_off": "no"}),
                "style_positive": ("BOOLEAN", {"default": True, "label_on": "yes", "label_off": "no"}),
                "style_negative": ("BOOLEAN", {"default": True, "label_on": "yes", "label_off": "no"}),
            },
        }

    RETURN_TYPES = ('STRING','STRING',)
    RETURN_NAMES = ('text_positive','text_negative',)
    FUNCTION = 'prompt_styler'
    CATEGORY = 'utils'

    def prompt_styler(self, text_positive, text_negative, style, log_prompt, style_positive, style_negative):
        # Process and combine prompts in templates
        # The function replaces the positive prompt placeholder in the template,
        # and combines the negative prompt with the template's negative prompt, if they exist.
        text_positive_styled, text_negative_styled = read_sdxl_templates_replace_and_combine(self.json_data, style, text_positive, text_negative)

        # If style_negative is disabled, set text_negative_styled to text_negative
        if not style_positive:
            text_positive_styled = text_positive
            if log_prompt:
                print(f"style_positive: disabled")

        # If style_negative is disabled, set text_negative_styled to text_negative
        if not style_negative:
            text_negative_styled = text_negative
            if log_prompt:
                print(f"style_negative: disabled")
 
        # If logging is enabled (log_prompt is set to "Yes"), 
        # print the style, positive and negative text, and positive and negative prompts to the console
        if log_prompt:
            print(f"style: {style}")
            print(f"text_positive: {text_positive}")
            print(f"text_negative: {text_negative}")
            print(f"text_positive_styled: {text_positive_styled}")
            print(f"text_negative_styled: {text_negative_styled}")

        return text_positive_styled, text_negative_styled
    
class SDXLPromptStylerAdvanced:

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(self):
        current_directory = os.path.dirname(os.path.realpath(__file__))
        self.json_data, styles = load_styles_from_directory(current_directory)
        
        return {
            "required": {
                "text_positive_g": ("STRING", {"default": "", "multiline": True}),
                "text_positive_l": ("STRING", {"default": "", "multiline": True}),
                "text_negative": ("STRING", {"default": "", "multiline": True}),
                "style": ((styles), ),
                "negative_prompt_to": (["Both", "G only", "L only"], {"default":"Both"}),
                "copy_to_l": ("BOOLEAN", {"default": False, "label_on": "yes", "label_off": "no"}),
                "log_prompt": ("BOOLEAN", {"default": False, "label_on": "yes", "label_off": "no"}),
            },
        }

    RETURN_TYPES = ('STRING','STRING','STRING','STRING','STRING','STRING',)
    RETURN_NAMES = ('text_positive_g','text_positive_l','text_positive','text_negative_g','text_negative_l','text_negative',)
    FUNCTION = 'prompt_styler_advanced'
    CATEGORY = 'utils'

    def prompt_styler_advanced(self, text_positive_g, text_positive_l, text_negative, style, negative_prompt_to, copy_to_l, log_prompt):
        # Process and combine prompts in templates
        # The function replaces the positive prompt placeholder in the template,
        # and combines the negative prompt with the template's negative prompt, if they exist.
        text_positive_g_styled, text_positive_l_styled, text_positive_styled, text_negative_g_styled, text_negative_l_styled, text_negative_styled = read_sdxl_templates_replace_and_combine_advanced(self.json_data, style, text_positive_g, text_positive_l, text_negative, negative_prompt_to, copy_to_l)
 
        # If logging is enabled (log_prompt is set to "Yes"), 
        # print the style, positive and negative text, and positive and negative prompts to the console
        if log_prompt:
            print(f"style: {style}")
            print(f"text_positive_g: {text_positive_g}")
            print(f"text_positive_l: {text_positive_l}")
            print(f"text_negative: {text_negative}")
            print(f"text_positive_g_styled: {text_positive_g_styled}")
            print(f"text_positive_l_styled: {text_positive_l_styled}")
            print(f"text_positive_styled: {text_positive_styled}")
            print(f"text_negative_g_styled: {text_negative_g_styled}")
            print(f"text_negative_l_styled: {text_negative_l_styled}")
            print(f"text_negative_styled: {text_negative_styled}")

        return text_positive_g_styled, text_positive_l_styled, text_positive_styled, text_negative_g_styled, text_negative_l_styled, text_negative_styled


