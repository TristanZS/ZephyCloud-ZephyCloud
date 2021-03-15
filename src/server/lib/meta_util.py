# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120
"""
This file contains tools to ease meta-programming.
It is compatible python 2.7+ and python 3
"""


class DynObject(dict):
    """
    Object which acts like flask 'g' object (and Javascript objects as well)
    ex:
      ex_obj = DynObject(foo=7, bar="hello")
      ex_obj.a_property = 25
      print(ex_obj.a_property)
    """
    def __init__(self, **kwargs):
        dict.__init__(self, kwargs)
        self.__dict__ = self


def get_subclasses(klass):
    """
    Get all subclasses of given class.
    It require all files containing subclasses to be already imported

    :param klass:   A class whom should have be inherited from
    :type klass:    class
    :return:        List of all subclasses of klass
    :rtype:         list[class]
    """
    result = set()
    for subclass in klass.__subclasses__():
        result.add(subclass)
        result.update(get_subclasses(subclass))
    return list(result)


class abstract_static(staticmethod):
    """
    Method decorator to specify a static method as abstract one
    See `abc` module for details

    Usage:
      class Example(object):
          __metaclass__ = abc.ABCMeta

          @abstract_static
          def my_abstract_static_method():
              return 5

      class Inherited(Example):
          @staticmethod
          def my_abstract_static_method():
              return 6

    """
    __slots__ = ()

    def __init__(self, func):
        super(abstract_static, self).__init__(func)
        func.__isabstractmethod__ = True

    __isabstractmethod__ = True
    

class func_decorator(object):
    """
    Helper decorator to create a more versatile decorator, able to:
      * use arguments
      * don't use arguments
      * use named and optional parameters
      * decorate a simple method
      * decorate a member function      
    
    Your decorator function should have the following arguments:
      :param func:              The decorated function
      :type func:               callable
      :param func_args:         The decorated function parameters used at call time
      :type func_args:          list[any]
      :param func_kwargs:       The decorated function named parameters used at call time
      :type func_args:          dict[str, any]
      And then all the parameter of your decorator
    
    Usage:
        # define our own decorator
        @func_decorator
        def my_decorator(func, func_args, func_kwargs, decorator_arg_example="default_value"):
            print("In my decorator before call, with arg " + repr(decorator_arg_example))
            result = func(*func_args, **func_kwargs)
            return result    

        # Our own decorator usage
        @my_decorator("defined_value")
        def my_function(classical_argument):
            print("inside decorated function, with argument " + repr(classical_argument))

        @my_decorator
        def another_decorated_function(classical_argument):
            print("inside another decorated function, with argument " + repr(classical_argument))

        class MyClass(object):
            @my_decorator(decorator_arg_example="example for a class member function")  
            def my_member_function(self):
                print("inside the class member")
                
        # Running the example:
        my_function(20)
        another_decorated_function(30)
        obj = MyClass()
        obj.my_member_function()
    """

    def __init__(self, decorator):
        self._decorator = decorator

    def __call__(self, *__args, **__kwargs):
        if len(__args) == 1 and len(__kwargs) == 0 and callable(__args[0]):
            def wrapper(*__wrapper_args, **__wrapper_kwargs):
                return self._decorator(__args[0], __wrapper_args, __wrapper_kwargs)
            return wrapper
        else:
            def wrapper(func, *__wrapper_args, **__wrapper_kwargs):
                def inner(*__inner_args, **__inner_kwargs):
                    return self._decorator(func, __inner_args, __inner_kwargs, *__args, **__kwargs)
                return inner
            return wrapper

    def __get__(self, obj, type=None):
        return self.__class__(self._decorator.__get__(obj, type))






