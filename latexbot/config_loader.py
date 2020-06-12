import json
import typing

class ConfigLoader:
    """
    A class to organize and help with config file loading.
    """

    def __init__(self):
        self.fields = {} # type: typing.Dict[str, typing.Tuple[typing.Callable[[typing.Any], typing.Any], typing.Callable[[typing.Any], typing.Any], type, typing.Any]]
    
    def field(self, name: str, field_type: type = None, load_handler: typing.Callable[[typing.Any], typing.Any] = None, 
              dump_handler: typing.Callable[[typing.Any], typing.Any] = None, default: typing.Any = None) -> None:
        """
        Declare a field.

        The load_handler should take the value of the field and return a processed
        value to be returned from load(). The dump_handler does the opposite.
        If not specified, it'll just be a function that returns its input.

        If the field type is specified, the type will be validated.

        If the field is incorrect, the handlers should raise a ValueError.
        """
        self.fields[name] = (load_handler, dump_handler, field_type, default)
    
    def _handle_field(self, config: typing.Dict[str, typing.Any], data: typing.Dict[str, typing.Any], 
                      field: str, handler: typing.Callable[[typing.Any], typing.Any], field_type: type, 
                      default: typing.Any, use_defaults: bool) -> str:
        """
        Handle a field during parsing or dumping.

        Returns an error message.
        """
        if field not in data:
            if field in config:
                return f"Warning: Field '{field}' not in config. Leaving unchanged."
            if use_defaults:
                config[field] = default
                return f"Warning: Field '{field}' not in config. Defaulting to '{default}'."
            return f"Warning: Field '{field}' not in config. Skipped."

        if not isinstance(data[field], field_type):
            if field in config:
                return f"Error: Field '{field}' needs to be of type '{field_type}'. Leaving unchanged."
            if use_defaults:
                config[field] = default
                return f"Error: Field '{field}' needs to be of type '{field_type}'. Defaulting to '{default}'."
            return f"Error: Field '{field}' needs to be of type '{field_type}'. Skipped."
        
        if handler is None:
            config[field] = data[field]
            return None
        
        try:
            config[field] = handler(data[field])
        except ValueError as e:
            if field in config:
                return f"While processing '{field}', an error occurred: '{e}' Field unchanged."
            if use_defaults:
                config[field] = default
                return f"While processing '{field}', an error occurred: '{e}' Defaulting to '{default}'."
            return f"While processing '{field}', an error occurred: '{e}' Skipped."
    
    def load(self, data: typing.Dict[str, typing.Any], config: typing.Dict[str, typing.Any], use_defaults=True) -> str:
        """
        Load config.

        Returns an error message and modifies the param config.

        If use_defaults is true (which is the default), when an error occurs during
        the parsing of a field, the default value will be used. Otherwise, that field
        will not be included. If the field is already present, it will not be updated
        on error.
        """
        errs = []

        for field, (handler, _, field_type, default) in self.fields.items():
            err = self._handle_field(config, data, field, handler, field_type, default, use_defaults)
            if err is not None:
                errs.append(err)
        return "\n".join(errs) if errs else None
    
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
            err = self._handle_field(config, data, field, handler, field_type, default, use_defaults)
            if err is not None:
                errs.append(err)
        return json.dumps(config), "\n".join(errs)
