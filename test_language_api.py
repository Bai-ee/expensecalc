from google.cloud import language_v1

# ath to your service account key file
key_file = "expenses-administration-07026ddc784a.json"

def analyze_text(text_content):
    """
    Analyzing Entities in a String

    Args:
    text_content The text content to analyze
    """

    client = language_v1.LanguageServiceClient.from_service_account_json(key_file)

    # Available types: PLAIN_TEXT, HTML
    type_ = language_v1.Document.Type.PLAIN_TEXT

    # Optional. If not specified, the language is automatically detected.
    # For list of supported languages:
    # https://cloud.google.com/natural-language/docs/languages
    document = {"content": text_content, "type_": type_}

    # Available values: NONE, UTF8, UTF16, UTF32
    encoding_type = language_v1.EncodingType.UTF8

    response = client.analyze_entities(request={'document': document, 'encoding_type': encoding_type})

    # Loop through entities returned from the API
    for entity in response.entities:
        print(f"Representative name for the entity: {entity.name}")
        print(f"Entity type: {language_v1.Entity.Type(entity.type_).name}")
        print(f"Salience score: {entity.salience}")
        print(f"Wikipedia URL: {entity.metadata.get('wikipedia_url', '-')}")
        print(f"Mid: {entity.metadata.get('mid', '-')}\n")

if __name__ == "__main__":
    text = "Google, headquartered in Mountain View, unveiled the new Android phone at the Consumer Electronic Show. Sundar Pichai said in his keynote that users love their new Android phones."
    analyze_text(text)
