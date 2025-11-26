from typing import AnyStr

from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PolicyGeneratorTemplate import PolicyGeneratorTemplate


class PatternPolicyGenerator(PolicyGeneratorTemplate):
    def __init__(self):
        super().__init__()

    def generate_policy(self, policy_contract, time_on=None, time_out=None):
        sig = "A(x0:int,x1:int)\nB(x0:int,x1:int)\nC(x0:int,x1:int)"
        policy = patterns_to_policy(policy_contract)
        seed = 1
        return seed, sig, policy


def patterns_to_policy(pat) -> AnyStr:
    interval = pat["interval"] if pat["interval"] is not None else "[0,30)"
    policy = pat.get("policy")
    if policy == "linear":
        return f"((ONCE {interval} A(w,x)) AND B(x,y)) AND (EVENTUALLY {interval} C(y,z))"
    elif policy == "triangle":
        return f"((ONCE {interval} A(x,y)) AND B(y,z)) AND (EVENTUALLY {interval} C(z,x))"
    else:
        return f"((ONCE {interval} A(w,x)) AND B(w,y)) AND (EVENTUALLY {interval} C(w,z))"
