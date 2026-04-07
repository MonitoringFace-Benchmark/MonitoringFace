from typing import List, Tuple, Dict, Any

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.Builders.ProcessorBuilder.PolicyConverters.PolicyConverterTemplate import PolicyConverterTemplate, PolicyTransformationException


class NegateMFOTLConverter(PolicyConverterTemplate):
    def __init__(self, name, path_to_project):
        pass

    def auto_convert(self, path_to_folder: str, input_file: str, path_to_output_folder: str, output_file: str,
                     source: InputOutputPolicyFormats, target: InputOutputPolicyFormats, params: Dict[str, Any]):
        with open(f"{path_to_folder}/{input_file}", 'r') as input_file:
            src_policy = input_file.read()

        if source == InputOutputPolicyFormats.NEGATED_MFOTL and target == InputOutputPolicyFormats.MFOTL:
            src_policy = src_policy.strip()
            if src_policy.startswith("NOT ("):
                src_policy = src_policy.replace("NOT (", "", 1)
                src_policy = src_policy[:-1]
            with open(f"{path_to_folder}/{output_file}", 'w') as f:
                f.write(f"NOT ({src_policy})")
        elif source == InputOutputPolicyFormats.MFOTL and target == InputOutputPolicyFormats.NEGATED_MFOTL:
            with open(f"{path_to_folder}/{output_file}", 'w') as f:
                f.write(f"NOT ({src_policy})")
        else:
            raise PolicyTransformationException(f"Incompatible conversion from {source} to {target}")

    @staticmethod
    def conversion_scheme() -> List[Tuple[InputOutputPolicyFormats, InputOutputPolicyFormats]]:
        return [
            (InputOutputPolicyFormats.NEGATED_MFOTL, InputOutputPolicyFormats.NEGATED_MFOTL),
            (InputOutputPolicyFormats.MFOTL, InputOutputPolicyFormats.NEGATED_MFOTL),
        ]
