from flask import request
from controller_base import Controller
from manager_base import RuntimeManager


# Define a runtime manager. However, if the base RuntimeManager is sufficient for your need, you
# can also just leverage it.
class CustomRuntimeManager(RuntimeManager):

    # For convenience and better code reuse, we recommend that every variable that is managed by
    # runtime manager should be defined as instance attribute. You can define them anywhere you
    # want, but make sure to avoid referencing before definition.
    # You can also define them again as class attributes for better type hinting, but it is purely
    # optional.
    some_current_status: int

    def load_actions(self) -> None:
        super(CustomRuntimeManager, self).load_actions()

        # To add any custom action, you need to override the function load_actions(). There are
        # several pre-defined actions such as '/finish' for ending the training, as well as
        # '/conf' for sending conf files to nodes (called by yourself). You can call super first
        # to load them, or re-define them yourself here.

        @self.app.route('/foo', methods=['POST'])
        def route_foo():
            some_param = request.args.get('param_name', type=str)
            self.on_route_foo(some_param)
            return ''   # make sure to have a return value, set to '' if not needed

        @self.app.route('foo2', methods=['GET'])
        def route_foo2():
            # You can make use of the thread pool executor for async execution.
            self.executor.submit(self.on_route_foo2)    # no need to pass self
            return ''

    # Define any function that does the work (e.g. manage and control the status of workers)

    def on_route_foo(self, some_param):
        pass

    def on_route_foo2(self):
        pass

    # Or you can also make use of the hooks for pre-defined actions. Note that some hooks have default
    # implementations, and it is optional to call super() to use.
    def _hook_start(self):
        super()._hook_start()
        print('This is hook start!')
        self.some_current_status = 0    # init an instance attribute (basically act as global variable)


# Define an controller for customization, or use the base Controller.
class CustomController(Controller):

    # You can customize the initialization of any part by overriding the corresponding init
    # function. Each function takes the corresponding part of appConfig read and process it.
    # Take this for example, the arg `links` is the 'links' part of appConfig file, and is used to
    # generate a link_ip file. It has a default implementation, which requires that the `links` to
    # be a list of link definition rules. By overriding this, you are also re-defining the data
    # structure requirements in `links`.
    def init_link(self, links) -> None:
        pass


# Define the run script as you wish. It can also be separated from the above class definitions -
# all up to yourself. The following is an example that you can make use of by few modifications.
if __name__ == '__main__':
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='AppConfig yaml file', required=True)
    args = parser.parse_args()

    dirname = os.path.abspath(os.path.dirname(__file__))
    # Change the CustomController to the controller class you defined.
    controller = CustomController(dirname)
    controller.init(os.path.join(dirname, args.config))
    # Change the CustomRuntimeManager to the runtime manager class you defined.
    controller.set_runtime_manager(CustomRuntimeManager(dirname))
    controller.run()

    # Example command to run: python3 controller_run_template.py -c appConfig-template.yml
