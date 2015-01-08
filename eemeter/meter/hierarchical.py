import scipy.optimize as opt
import numpy as np

class MeterBase(object):
    def __init__(self,**kwargs):
        if "input_mapping" in kwargs:
            self.input_mapping = kwargs["input_mapping"]
        else:
            self.input_mapping = {}
        if "output_mapping" in kwargs:
            self.output_mapping = kwargs["output_mapping"]
        else:
            self.output_mapping = {}

    def evaluate(self,**kwargs):
        mapped_inputs = self.apply_input_mapping(kwargs)
        result = self.evaluate_mapped_inputs(**mapped_inputs)
        mapped_output = self.apply_output_mapping(result)
        return mapped_output

    def apply_input_mapping(self,inputs):
        mapped_inputs = {}
        for k,v in inputs.iteritems():
            if k in self.input_mapping:
                new_key = self.input_mapping[k]
                if new_key in self.input_mapping:
                    message = "input_mapping for '{}' would overwrite existing key."
                    raise ValueError(message)
                mapped_inputs[new_key] = v
            else:
                mapped_inputs[k] = v
        return mapped_inputs

    def apply_output_mapping(self,outputs):
        mapped_outputs = {}
        for k,v in outputs.iteritems():
            if k in self.output_mapping:
                new_key = self.output_mapping[k]
                if new_key in self.output_mapping:
                    message = "output_mapping for '{}' would overwrite existing key."
                    raise ValueError(message)
                mapped_outputs[new_key] = v
            else:
                mapped_outputs[k] = v
        return mapped_outputs

    def evaluate_mapped_inputs(self,**kwargs):
        raise NotImplementedError

class SequentialMeter(MeterBase):
    def __init__(self,sequence,**kwargs):
        super(SequentialMeter,self).__init__(**kwargs)
        assert all([issubclass(meter.__class__,MeterBase)
                    for meter in sequence])
        self.sequence = sequence

    def evaluate_mapped_inputs(self,**kwargs):
        result = {}
        for meter in self.sequence:
            meter_result = meter.evaluate(**kwargs)
            for k,v in meter_result.iteritems():
                if k in result:
                    message = "unexpected repeated metric ({}). " \
                              "A different input_mapping or " \
                              "output_mapping may fix this overlap."
                    raise ValueError(message.format(k))
                result[k] = v
        return result

class TemperatureSensitivityParameterOptimizationMeter(MeterBase):
    def __init__(self,fuel_unit_str,fuel_type,temperature_unit_str,model,**kwargs):
        super(self.__class__,self).__init__(**kwargs)
        self.fuel_unit_str = fuel_unit_str
        self.fuel_type = fuel_type
        self.temperature_unit_str = temperature_unit_str
        self.model = model

    def evaluate_mapped_inputs(self,consumption_history,weather_source,**kwargs):
        consumptions = consumption_history.get(self.fuel_type)
        usages = [c.to(self.fuel_unit_str) for c in consumptions]
        observed_temps = weather_source.get_average_temperature(consumptions,self.temperature_unit_str)
        params = self.model.parameter_optimization(usages,observed_temps)
        return {"temp_sensitivity_params": params}


class DummyMeter(MeterBase):
    def evaluate_mapped_inputs(self,**kwargs):
        result = {"value": kwargs["value"]}
        return result
