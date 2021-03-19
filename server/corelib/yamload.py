"""
Yaml config load
"""
import os
import re
import sys
import yaml
import logging


class ConfigLoader(object):
    dynamic_pattern = re.compile('{[a-z]+[.[a-z]+]*}')

    def __init__(self, cfg_path=''):
        self.config, self.has_import = None, []
        self.cfg_dir = os.path.dirname(cfg_path)
        self.load(cfg_path)

    def load(self, cfg_path):
        self.config = self.load_file(cfg_path)
        self.load_import(self.config)
        self.load_dynamic(self.config)
        sys.stdout.flush()
        return self.config

    @staticmethod
    def load_file(cfg_path):
        assert os.path.isfile(cfg_path), f'[{cfg_path}] is not file'
        with open(cfg_path, 'rb') as f:
            content = yaml.load(f, Loader=yaml.FullLoader)
        return content

    def load_import(self, config):
        if not isinstance(config, dict):
            return config
        if 'import' not in config:
            return config
        import_files = config['import']
        if import_files and (isinstance(import_files, set) or isinstance(import_files, list)):
            import_files = config.pop('import')
            if isinstance(import_files, list):
                import_files = set(import_files)
            for import_file in import_files:
                if import_file in self.has_import:
                    logging.warning(f'[{import_file}] has imported!')
                    continue
                self.has_import.append(import_file)
                import_path = os.path.join(self.cfg_dir, '%s.yml' % import_file)
                import_config = self.load_file(import_path)
                config = self.compare(config, import_config)
                logging.info(f'[{import_file}] is imported ~')
        return self.load_import(config)

    def load_dynamic(self, config):
        """
        can not deal list
        :param config:
        """
        for key, value in config.items():
            if isinstance(value, dict):
                self.load_dynamic(value)
                continue
            if not isinstance(value, str):
                continue
            matches = self.dynamic_pattern.findall(str(value))
            if not matches:
                continue
            while matches:
                for match in matches:
                    config[key] = re.sub(match, str(self.get_config(match[1:-1])), config[key])
                matches = self.dynamic_pattern.findall(config[key])

    def compare(self, new_config, old_config):
        for key, value in old_config.items():
            if key not in new_config:
                new_config[key] = value
            elif isinstance(value, dict) and isinstance(new_config[key], dict):
                self.compare(new_config[key], value)
        return new_config

    def get_config(self, key=None):
        current_config = self.config
        if not key:
            return current_config
        sub_keys = key.lower().split('.')
        for sub_key in sub_keys:
            assert isinstance(current_config, dict)
            current_config = current_config[sub_key]
        return current_config

    def get(self, key=None):
        return self.get_config(key)
