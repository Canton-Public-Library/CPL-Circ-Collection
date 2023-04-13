import configparser

def load_config(file):
    """Reads and returns config file."""
    config = configparser.ConfigParser()
    config.read_file(open(file, "r"))
    return config            
