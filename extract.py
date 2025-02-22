import requests
from bs4 import BeautifulSoup
import html2text

def extract_text_from_url(url: str) -> str:
    """
    Fetches and extracts structured text content from a given webpage URL.

    This function sends an HTTP GET request to the specified URL, retrieves the HTML content,
    parses it using BeautifulSoup, removes irrelevant tags like script and style, and then
    converts the remaining HTML into a structured, Markdown-like text format using html2text.

    Args:
        url (str): The URL of the webpage from which to extract text.

    Returns:
        str: The extracted structured text content from the webpage.
             Returns an error message as a string if there is an issue fetching the webpage.
    """

    # Define headers to mimic a browser request to avoid being blocked by some websites.
    headers: dict = {'User-Agent': 'Mozilla/5.0'}
    try:
        # Send a GET request to the URL with a timeout of 10 seconds.
        response = requests.get(url, headers=headers, timeout=10)
        # Raise an HTTPError for bad responses (4xx or 5xx).
        response.raise_for_status()
    except requests.RequestException as e:
        # Handle any request exceptions (e.g., network errors, timeouts).
        return f"Error fetching the webpage: {e}"

    # Parse the HTML content of the response using BeautifulSoup.
    soup: BeautifulSoup = BeautifulSoup(response.text, 'html.parser')

    # Remove unwanted tags that are not typically part of the main textual content.
    # These include script, style, meta, and noscript tags.
    for script in soup(['script', 'style', 'meta', 'noscript']):
        script.extract()  # Remove each tag from the BeautifulSoup object.

    # Initialize the HTML to Markdown converter from the html2text library.
    markdown_converter: html2text.HTML2Text = html2text.HTML2Text()
    markdown_converter.ignore_links = False   # Set to False to keep hyperlinks in the output.
    markdown_converter.ignore_images = True   # Set to True to remove images from the output.
    markdown_converter.ignore_tables = False  # Set to False to preserve table structure in the output.

    # Convert the parsed HTML (now without unwanted tags) to structured Markdown-like text.
    # The `handle` method processes the BeautifulSoup object and returns the text.
    structured_text: str = markdown_converter.handle(str(soup))

    # Return the extracted structured text, removing any leading/trailing whitespace.
    return structured_text.strip()

if __name__ == "__main__":
    """
    Main execution block to demonstrate the text extraction from a URL.

    Prompts the user to enter a website URL, then calls the `extract_text_from_url` function
    to get the text content. Finally, it prints the extracted text to the console, preceded by a separator.
    """
    # Prompt the user to enter a website URL.
    url: str = input("Enter website URL: ")
    # Extract text content from the provided URL using the extract_text_from_url function.
    text_content: str = extract_text_from_url(url)
    # Print a separator and then the extracted text content to the console.
    print("\n--- Extracted Text ---\n")
    print(text_content)