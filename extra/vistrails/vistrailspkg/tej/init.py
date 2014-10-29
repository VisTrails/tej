from vistrails.core.modules.vistrails_module import Module


class Queue(Module):
    _output_ports = [('message', '(basic:String)')]

    def compute(self):
        self.set_output('message', "Hello world")


_modules = [Queue]
