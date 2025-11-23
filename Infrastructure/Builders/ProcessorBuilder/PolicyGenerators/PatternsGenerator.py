from typing import AnyStr

from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PolicyGeneratorTemplate import PolicyGeneratorTemplate


class PatternsGenerator(PolicyGeneratorTemplate):
    def __init__(self):
        super().__init__()

    def generate_policy(self, policy_contract, time_on=None, time_out=None):
        sig = "A(int,int)\nB(int,int)\nC(int,int)"
        policy = patterns_to_policy(policy_contract)
        seed = 1
        return seed, sig, policy


def patterns_to_policy(pat) -> AnyStr:
    interval = pat["interval"] if pat["interval"] is not None else "[0,30)"
    if pat["linear"] is not None:
        return f"((ONCE {interval} A(w,x)) AND B(x,y)) AND (EVENTUALLY {interval} C(y,z))"
    elif pat["triangle"] is not None:
        return f"((ONCE {interval} A(x,y)) AND B(y,z)) AND (EVENTUALLY {interval} C(z,x))"
    else:
        return f"((ONCE {interval} A(w,x)) AND B(w,y)) AND (EVENTUALLY {interval} C(w,z))"