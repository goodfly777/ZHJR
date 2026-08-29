from pathlib import Path


def load_prompt(file_name: str) -> str:

    prompt_path = Path(__file__).parent / "jinja2" / f"{file_name}.jinja2"
    return prompt_path.read_text(encoding="utf-8")

if __name__ == '__main__':

    print(Path(__file__).parent / "jinja2" / f"123.jinja2")