def execute(self, inputs, outputs, external_modules, gvm):
    print "Executing first execution state ..."
    print inputs
    print outputs
    outputs["data_output_port1"] = inputs["data_input_port1"] + 10.0
    self.print_state_information()
    return 3
