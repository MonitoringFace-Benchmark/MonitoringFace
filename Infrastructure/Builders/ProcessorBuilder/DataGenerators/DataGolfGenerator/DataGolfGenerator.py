import re
from dataclasses import fields
from typing import AnyStr

from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGeneratorTemplate import DataGeneratorTemplate
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGolfGenerator.DataGolfContract import DataGolfContract
from Infrastructure.Builders.ProcessorBuilder.ImageManager import ImageManager, Processor
from Infrastructure.Monitors.MonitorExceptions import GeneratorException
from Infrastructure.constants import DATAGOLF_POLICY_CHECK, COMMAND_KEY, WORKDIR_KEY, WORKDIR_VAL, VOLUMES_KEY


DEFAULT_SEED = -1


class DataGolfGenerator(DataGeneratorTemplate):
    def __init__(self, name, path_to_build):
        self.image = ImageManager(name, Processor.DataGenerators, path_to_build)

    def run_generator(self, data_golf_contract_params, time_on=None, time_out=None):
        data_golf_contract_params["tup_ts"] = list(range(data_golf_contract_params["trace_length"] + 1))
        valid_fields = {f.name for f in fields(DataGolfContract)}
        data_golf_contract = DataGolfContract(
            **{k: v for k, v in data_golf_contract_params.items() if k in valid_fields})

        inner_contract = dict()
        inner_contract[COMMAND_KEY] = ["/usr/local/bin/datagolf"] + data_golf_contract_to_command(data_golf_contract)
        inner_contract[VOLUMES_KEY] = {data_golf_contract.path: {'bind': '/data', 'mode': 'rw'}}
        inner_contract[WORKDIR_KEY] = WORKDIR_VAL

        seed = data_golf_contract.seed if data_golf_contract.seed else DEFAULT_SEED

        out, code = self.image.run(inner_contract, time_on=time_on, time_out=time_out)
        if code != 0:
            print(f"Code {code}\nOutput:\n{out}")
            raise GeneratorException(f"DataGolf generator failed (exit_code={code}). Output:\n{out}")

        try:
            if "@" not in out:
                raise ValueError("missing '@' separator in datagolf output")
            raw_split = out.split("@", 1)
            prefix = raw_split[0]

            if data_golf_contract.oracle:
                try:
                    with open(f"{data_golf_contract.path}/result/prefix_{str(data_golf_contract.trace_length)}", "w") as file:
                        file.write(prefix)
                except Exception():
                    pass

            remove_prefix = "@" + raw_split[1]
            if "Trace:" not in remove_prefix:
                raise ValueError("missing 'Trace:' marker in datagolf output")

            csv = stdout_to_csv(remove_prefix.split("Trace:")[0].rstrip())
            return seed, csv, code
        except Exception as e:
            cmd = inner_contract.get(COMMAND_KEY) if 'inner_contract' in locals() else None
            msg = (
                f"Failed to parse datagolf output: {e}\n"
                f"Command: {cmd}\n"
                f"Exit code: {code}\n"
                f"Raw output:\n{out}"
            )
            raise GeneratorException(msg)

    def check_policy(self, path_inner, signature, formula) -> bool:
        inner_contract = dict()
        inner_contract[COMMAND_KEY] = ["/usr/local/bin/datagolf", "-sig", signature, "-formula", formula, "-check"]
        inner_contract[VOLUMES_KEY] = {path_inner: {'bind': '/data', 'mode': 'ro'}}
        inner_contract[WORKDIR_KEY] = "/data"

        out, code = self.image.run(inner_contract, None, None)
        if code != 0:
            return False
        else:
            out = out.strip()
            return out.__eq__(DATAGOLF_POLICY_CHECK)


def stdout_to_csv(in_str: AnyStr):
    res = []
    ts_pattern = r"^\d+"
    empty_line_pattern = r"^\d+;\s*$"
    for (tp, raw) in enumerate(filter(None, in_str.split("@"))):
        ts = re.match(ts_pattern, raw).group()
        if re.match(empty_line_pattern, raw):
            res.append(f"Placeholder, tp={tp}, ts={ts}")
        else:
            cleaned = re.sub(r"^\d+\s*", "", raw).strip()
            for line in cleaned.split("\n"):
                cleaned_line = line.strip()
                name, tuples = cleaned_line.split(" ", 1)
                prefix = f"{name}, tp={tp}, ts={ts}"

                tuple_lists = [
                    [item.strip() for item in tup.split(',') if item.strip() != '']
                    for tup in re.findall(r"\(([^()]*)\)", tuples)
                ]

                if tuple_lists != [[]]:
                    for tup in tuple_lists:
                        tup_str = ", ".join([f"x{i+1}={val}" for i, val in enumerate(tup)])
                        res.append(f"{prefix}, {tup_str}")
                else:
                    res.append(prefix)
    return "\n".join(res)


def data_golf_contract_to_command(contract) -> list[AnyStr]:
    if contract.sig_file == "":
        contract.sig_file = "signature.sig"

    if contract.formula == "":
        contract.formula = "formula.mfotl"

    args = ["-sig", contract.sig_file, "-formula", contract.formula]
    if hasattr(contract, 'no_rewrite') and contract.no_rewrite is not None:
        if contract.no_rewrite:
            args += ["-no_rw"]

    args += ["-nonewlastts", "-tup-ts", ",".join(map(str, contract.tup_ts)), "-tup-amt",
             str(contract.tup_amt), "-tup-val", str(contract.tup_val)]

    if contract.seed:
        args += ["-tg_seed", str(contract.seed)]

    if contract.oracle:
        args += ["-tup-out", f"result/result_{str(contract.trace_length)}.res"]

    return args
