import hashlib

def create_decklist_id(decklist_data: dict[str, int]):
    """
    Creates a hash string based on the input dictionary values.

    Parameters:
    decklist_data (dict): A dictionary with string keys and integer values.

    Returns:
    str: A hexadecimal hash string.
    """
    # Concatenate keys and values into a single string
    concat_string = ''.join(f"{key}:{value}" for key, value in decklist_data.items())

    # Create a SHA-256 hash of the concatenated string
    hash_object = hashlib.sha256(concat_string.encode())

    # Return the hexadecimal representation of the hash
    return hash_object.hexdigest()