
class YamoException(Exception):
    pass


class ConfigError(YamoException):
    pass


class IncompleteDocumentData(Exception):
    pass


class ArgumentError(Exception):

    def __init__(self, obj, val):
        self.obj = obj
        self.val = val

    def __str__(self):
        return "Object {} encounters wrong argument {}" \
            "".format(self.obj, self.val)


class ValidationError(YamoException):

    def __init__(self, cls, attr, val):
        self.cls = cls
        self.attr = attr
        self.val = val

    def __str__(self):
        return "Validation failed on {}: trying to set {} <- <{}>(type:{})" \
            "".format(self.cls, self.attr,
                      self.val, type(self.val))


class DeserializationError(YamoException):

    def __init__(self, field, val):
        self.fld = field
        self.val = val

    def __str__(self):
        msg = "Can't deserialize value for field {}: {}"
        return msg.format(self.fld, self.val)
