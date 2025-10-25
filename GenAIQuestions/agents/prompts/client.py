new_question_prompt="""Given {data}, generate a new perseus question"""
new_svg_prompt="""Generate appropriate SVGs for each of the prompts in - {prompts}"""
new_images_prompt="""Given {new_json}, extract and generate appropraite prompts. Use the image {image_file} as a guide."""
rebuild_json_prompt="""Rebuild this json: {new_json}, using: {prompts}"""
 