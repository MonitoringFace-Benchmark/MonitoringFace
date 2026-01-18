# Monitors

## Rules

1. Each monitor **must** implement `AbstractMonitorTemplate`.
2. The **folder name**, **file name**, and **class name** must be identical (case-sensitive) for automatic discovery.

## Example

```
Monitors/
  TimelyMon/
    TimelyMon.py   → class TimelyMon(AbstractMonitorTemplate)
```

```python
# TimelyMon/TimelyMon.py
class TimelyMon(AbstractMonitorTemplate):
    ...
```

Mismatched names will prevent the monitor from being discovered.

## Abstract Methods

**`init(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any])`**
The constructor connects the monitor to its underlying Docker image, the parameters dictionary contains all the parameters and options for the tool and 
additionally required converters or utilities. Name identifies the underlying Docker image, it should also match the class name.

**`preprocessing(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr)`**  
Parses the standard data, policy, and signature input formats into a tool-specific format. This step may involve the use of converters. All changes should be written to the temporary and private `path_to_folder/scratch` folder.

**`run_offline(self, time_on=None, time_out=None)`**  
Runs the monitor on a complete dataset (offline) with optional lower and upper time limits. This method requires implementing the command-construction logic that accesses the underlying Docker image. Set the necessary parameters and flags accordingly.

**`postprocessing(self, stdout_input: AnyStr)`**  
Transforms the tool output into an appropriate format for verification. Converters or utilities may also be used in this step.

**`variable_order(self)`**  
Returns the order of free variables (if any) in the results returned by the monitor.
