import json
import typing

class ConfigLoader:
    """
    A class to organize and help with config file parsing.
    """

    def __init__(self):
        self.fields = {} # type: typing.Dict[str, typing.Tuple[typing.Callable[[typing.Any], typing.Any], typing.Callable[[typing.Any], typing.Any], type, typing.Any]]
    
    def field(self, name: str, field_type: type = None, parse_handler: typing.Callable[[typing.Any], typing.Any] = None, 
              dump_handler: typing.Callable[[typing.Any], typing.Any] = None, default: typing.Any = None) -> None:
        """
        Declare a field.

        The parse_handler should take the value of the field and return a processed
        value to be returned from parse(). The dump_handler does the opposite.
        If not specified, it'll just be a function that returns its input.

        If the field type is specified, the type will be validated.

        If the field is incorrect, the handlers should raise a ValueError.

        If the field does not appear in the file/dict when parsing/dumping, None will
        be given to the handler.
        """
        self.fields[name] = (parse_handler, dump_handler, field_type, default)
    
    def _handle_field(self, data: typing.Dict[str, typing.Any], field: str, 
                      handler: typing.Callable[[typing.Any], typing.Any], field_type: type, 
                      default: typing.Any, use_defaults: bool) -> typing.Tuple[typing.Any, str]:
        """
        Handle a field during parsing or dumping.

        Returns a tuple of the value and the error. Either may be None.
        """
        if field not in data:
            try:
                return handler(None), f"Warning: Field '{field}' not in config."
            except ValueError:
                if use_defaults:
                    return default, f"Warning: Field '{field}' not in config. Defaulting to '{default}'."
                else:
                    return None, f"Warning: Field '{field}' not in config. Skipped."
        else:
            if not isinstance(data[field], field_type):
                if use_defaults:
                    return default, f"Error: Field '{field}' needs to be of type '{field_type}'. Defaulting to '{default}'."
                else:
                    return None, f"Error: Field '{field}' needs to be of type '{field_type}'. Skipped."
            if handler is None:
                return data[field], None
            else:
                try:
                    return handler(data[field]), None
                except ValueError as e:
                    if use_defaults:
                        return default, f"Error while processing field '{field}': '{e}' Defaulting to '{default}'."
                    else:
                        return None, f"Error while processing field '{field}': '{e}' Skipped."
    
    def parse(self, filename, use_defaults=True) -> typing.Tuple[typing.Dict[str, typing.Any], str]:
        """
        Parse a file.

        Returns a tuple of the config and an error message.

        If use_defaults is true (which is the default), when an error occurs during
        the parsing of a field, the default value will be used. Otherwise, that field
        will not be included.
        """
        with open(filename, "r") as f:
            data = json.load(f)
        config = {}
        errs = []

        for field, (handler, _, field_type, default) in self.fields.items():
            value, err = self._handle_field(data, field, handler, field_type, default, use_defaults)
            if value is not None:
                config[field] = value
            if err is not None:
                errs.append(err)
        return config, "\n".join(errs)
    
    def dump(self, data: typing.Dict[str, typing.Any], use_defaults=True) -> typing.Tuple[str, str]:
        """
        Convert a config into a string.

        Returns a tuple of the data and an error message.

        If use_defaults is true (which is the default), when an error occurs during
        the conversion of a field, or if that field does not exist in the data, the
        default value will be used. Otherwise, that field will not be included.
        """
        config = {}
        errs = []
        for field, (_, handler, field_type, default) in self.fields.items():
            value, err = self._handle_field(data, field, handler, field_type, default, use_defaults)
            if value is not None:
                config[field] = value
            if err is not None:
                errs.append(err)
        return json.dumps(config), "\n".join(errs)
