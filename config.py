import configparser

def load_config(file):
    """Reads and returns config file."""
    config = configparser.ConfigParser()
    config.read(file)
    return config
