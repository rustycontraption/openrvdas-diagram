class UserInputError(Exception):
    code = "user_input_error"

    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self):
        return {"code": self.code, "message": self.message, "details": self.details}


class MissingTemplateFileError(UserInputError):
    code = "missing_template_file"

    def __init__(self, config_file, template_file):
        super().__init__(
            f"{config_file} includes {template_file}, which was not found in the template directory",
            {"config_file": config_file, "template_file": template_file},
        )


class UnknownLoggerTemplateError(UserInputError):
    code = "unknown_logger_template"

    def __init__(self, config_file, logger, logger_template):
        super().__init__(
            f"logger {logger} in {config_file} uses logger_template {logger_template}, "
            "which is not defined in any of the files it includes",
            {"config_file": config_file, "logger": logger, "logger_template": logger_template},
        )


class InvalidYamlError(UserInputError):
    code = "invalid_yaml"

    def __init__(self, file, line=None):
        location = f"{file} line {line}" if line is not None else file
        details = {"file": file}
        if line is not None:
            details["line"] = line
        super().__init__(f"{location} is not valid YAML", details)
