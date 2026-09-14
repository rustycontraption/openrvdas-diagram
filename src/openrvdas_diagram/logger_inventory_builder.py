import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PLACEHOLDER_PATTERN = re.compile(r"<<([^<>]+)>>")


@dataclass
class Reader:
    class_name: str
    kwargs: dict = field(default_factory=dict)


@dataclass
class Transform:
    class_name: str
    kwargs: dict = field(default_factory=dict)


@dataclass
class Writer:
    class_name: str
    kwargs: dict = field(default_factory=dict)
    transforms: list = field(default_factory=list)


@dataclass(repr=False)
class Logger:
    name: str
    readers: list = field(default_factory=list)
    transforms: list = field(default_factory=list)
    writers: list = field(default_factory=list)
    variables: dict = field(default_factory=dict)

    def __repr__(self):
        return (
            f"Logger(name={self.name!r}, readers={self.readers!r}, "
            f"transforms={self.transforms!r}, writers={self.writers!r})"
        )


class LoggerInventory(dict):
    def add_logger(self, yaml_file, logger):
        self.setdefault(yaml_file, {})[logger.name] = logger


class LoggerInventoryBuilder:
    def _load_yaml(self, path):
        with open(path) as file:
            return yaml.safe_load(file)

    def _load_templates(self, templates, template_dir):
        logger_templates = {}
        for template in templates:
            data = self._load_yaml(template_dir / Path(template).name)
            logger_templates.update(data.get("logger_templates", {}))
        return logger_templates

    def _resolve_vars(self, value, variables):
        if isinstance(value, str):
            match = PLACEHOLDER_PATTERN.fullmatch(value)
            if match:
                return variables.get(match.group(1), value)
            return PLACEHOLDER_PATTERN.sub(lambda match: str(variables.get(match.group(1), match.group(0))), value)
        if isinstance(value, dict):
            return {key: self._resolve_vars(item, variables) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_vars(item, variables) for item in value]
        return value

    @staticmethod
    def _as_list(value):
        if value is None:
            return []
        return value if isinstance(value, list) else [value]

    @staticmethod
    def _parse_readers(readers):
        return [
            Reader(class_name=entry.get("class"), kwargs=entry.get("kwargs") or {})
            for entry in LoggerInventoryBuilder._as_list(readers)
            if entry.get("class")
        ]

    @staticmethod
    def _parse_transforms(transforms):
        return [
            Transform(class_name=entry.get("class"), kwargs=entry.get("kwargs") or {})
            for entry in LoggerInventoryBuilder._as_list(transforms)
            if entry.get("class")
        ]

    def _flatten_writers(self, writers, transforms=()):
        flattened_writers = []
        for writer in self._as_list(writers):
            class_name = writer.get("class")
            kwargs = writer.get("kwargs", {}) or {}
            if class_name == "ComposedWriter":
                branch_transforms = transforms + tuple(self._parse_transforms(kwargs.get("transforms")))
                flattened_writers.extend(self._flatten_writers(kwargs.get("writers"), branch_transforms))
            else:
                flattened_writers.append(Writer(class_name=class_name, kwargs=kwargs, transforms=list(transforms)))
        return flattened_writers

    @staticmethod
    def _filter_active_configs(configs_by_name, candidate_names):
        for name in candidate_names:
            config = configs_by_name.get(name) or {}
            if config.get("readers"):
                return config
        return {}

    def _resolve_logger_config(self, definition, templates, inline_configs):
        if "logger_template" in definition:
            template = templates[definition["logger_template"]]
            variables = definition.get("variables", {}) or {}
            configs = template.get("configs", {}) or {}
            config = self._filter_active_configs(configs, [config_name for config_name in configs if config_name != "off"])
            return self._resolve_vars(config, variables)
        if "configs" in definition:
            return self._filter_active_configs(inline_configs, definition["configs"])
        return {}

    def _find_config_files(self, config_dir):
        return sorted(
            path for pattern in ("*.yml", "*.yaml") for path in config_dir.glob(pattern)
        )

    def collectAndParseLoggers(self, config_dir, template_dir):
        config_dir = Path(config_dir)
        template_dir = Path(template_dir)
        inventory = LoggerInventory()
        for path in self._find_config_files(config_dir):
            data = self._load_yaml(path)
            templates = self._load_templates(data.get("includes", []) or [], template_dir)
            inline_configs = data.get("configs", {}) or {}
            for name, definition in (data.get("loggers", {}) or {}).items():
                config = self._resolve_logger_config(definition, templates, inline_configs)
                readers = self._parse_readers(config.get("readers"))
                if not readers:
                    continue
                logger_transforms = self._parse_transforms(config.get("transforms"))
                inventory.add_logger(path.stem, Logger(
                    name=name,
                    readers=readers,
                    transforms=logger_transforms,
                    writers=self._flatten_writers(config.get("writers"), tuple(logger_transforms)),
                    variables=definition.get("variables", {}) or {},
                ))
        return inventory
