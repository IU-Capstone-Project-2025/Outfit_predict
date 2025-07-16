import os
import re
from typing import Union

import torch
import transformers.dynamic_module_utils
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor
from transformers.dynamic_module_utils import get_imports


def fixed_get_imports(filename: Union[str, os.PathLike]) -> list[str]:
    if not str(filename).endswith("modeling_florence2.py"):
        return get_imports(filename)
    imports = get_imports(filename)
    # Only remove flash_attn if it's actually in the imports list
    if "flash_attn" in imports:
        imports.remove("flash_attn")
    return imports


transformers.dynamic_module_utils.get_imports = fixed_get_imports

# Florence-2 setup

device = "cuda" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Florence-2-base", torch_dtype=torch_dtype, trust_remote_code=True
).to(device)
processor = AutoProcessor.from_pretrained(
    "microsoft/Florence-2-base", trust_remote_code=True
)


def extract_item_description(caption: str) -> str:
    """
    Извлекает краткое описание вещи из полного caption.
    Например:
    'The image shows a woman wearing black thigh high boots and gloves,
    standing on the floor with a wall in the background.
    The image is slightly blurred, giving it a dreamy, ethereal feel.'
    -> 'black thigh high boots and gloves'
    'The image shows a person holding a black handbag in their hand.
    The handbag is slightly blurred, giving it a dreamy, ethereal quality.'
    -> 'a black handbag . The handbag is slightly blurred, giving it a dreamy, ethereal quality.'
    Если не найдено — возвращает caption как есть.
    """
    # 1. Ищем "wearing ..." или "holding ..."
    match = re.search(r"(?:wearing|holding) ([^.,;]+)", caption)
    if match:
        return match.group(1).strip()
    # 2. Ищем после 'The image shows ...' до первой точки
    match = re.search(
        r"The image shows [^.,;]*? (wearing|holding)? ?([^.,;]+)", caption
    )
    if match and match.group(2):
        # Если есть wearing/holding, уже обработано выше, иначе берём group(2)
        return match.group(2).strip()
    # 3. Если есть повторное упоминание предмета (например, 'The handbag is ...'), берём это предложение
    match = re.search(r"(The [a-zA-Z ]+? is [^.,;]+)", caption)
    if match:
        return match.group(1).strip()
    # 4. Если caption начинается с 'a/an/the', берём первые 2-3 слова
    match = re.match(r"(a|an|the) ([^.,]+)", caption, re.IGNORECASE)
    if match:
        return match.group(2).strip()
    # 5. Если ничего не нашли, возвращаем caption как есть
    return caption.strip()


def generate_caption(image: Image.Image) -> dict:
    prompt = "<DETAILED_CAPTION>"
    inputs = processor(text=prompt, images=image, return_tensors="pt").to(
        device, torch_dtype
    )
    generated_ids = model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=128,
        num_beams=3,
        do_sample=False,
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    short_caption = extract_item_description(generated_text)
    return {"caption": generated_text, "short_caption": short_caption}


# Еще можно сделать так:
# from transformers import pipeline

# captioner = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")
# captioner("https://huggingface.co/datasets/Narsil/image_dummy/resolve/main/parrots.png")
# ## [{'generated_text': 'two birds are standing next to each other '}]
