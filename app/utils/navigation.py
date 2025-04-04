from streamlit.runtime.scriptrunner import RerunData, RerunException
from streamlit.source_util import get_pages


def switch_page(page_name: str):
    """
    https://github.com/arnaudmiribel/streamlit-extras/blob/main/src/streamlit_extras/switch_page_button/__init__.py
    """
    def standardize_name(name: str) -> str:
        return name.lower().replace("_", " ")

    page_name = standardize_name(page_name)

    pages = get_pages("streamlit_app.py")  # OR whatever your main page is called

    for page_hash, config in pages.items():
        if standardize_name(config["page_name"]) == page_name:
            raise RerunException(
                RerunData(
                    page_script_hash=page_hash,
                    page_name=page_name,
                )
            )

    page_names = [standardize_name(config["page_name"]) for config in pages.values()]

    raise ValueError(f"Could not find page '{page_name}'. Must be one of {page_names}")
