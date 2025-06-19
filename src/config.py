import configparser
import os

def read_config():
    """Read configuration from config.ini file"""
    config = configparser.ConfigParser()
    
    # Get the path to config.ini (one level up from src directory)
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    
    # Check if config file exists
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Read the config file
    config.read(config_path)
    
    # Convert to flat dictionary for easier access
    config_dict = {}
    
    # Add DEFAULT section items (if any)
    config_dict.update(dict(config.defaults()))
    
    # Add all sections and their items
    for section_name in config.sections():
        section_items = dict(config[section_name])
        # Add section items directly to config_dict (flattened)
        config_dict.update(section_items)
    
    return config_dict
