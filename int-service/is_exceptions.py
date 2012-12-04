# -*- coding: utf-8 -*-
import exceptions

#Define exceptions
class ISError(Exception): pass
class ISInvalidInputParametersError(ISError): pass
class ISInvalidAgeError(ISError): pass
class ISInvalidSexError(ISError): pass
