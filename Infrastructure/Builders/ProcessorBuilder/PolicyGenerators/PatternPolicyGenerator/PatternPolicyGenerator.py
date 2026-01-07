from typing import AnyStr

from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PolicyGeneratorTemplate import PolicyGeneratorTemplate


class PatternPolicyGenerator(PolicyGeneratorTemplate):
    def __init__(self, name, path_to_build):
        super().__init__()

    def generate_policy(self, policy_contract, time_on=None, time_out=None):
        sig = "A(x0:int,x1:int)\nB(x0:int,x1:int)\nC(x0:int,x1:int)"
        policy = patterns_to_policy(policy_contract)
        seed = 1
        return (seed, sig, policy), 0  # Return tuple and exit code like MfotlPolicyGenerator


def patterns_to_policy(pat) -> AnyStr:
    interval = pat.get("interval") if pat.get("interval") is not None else "[0,30)"
    
    # Determine which pattern to use based on which field is set
    if pat.get("linear"):
        policy = "linear"
    elif pat.get("triangle"):
        policy = "triangle"
    elif pat.get("star"):
        policy = "star"
    else:
        # Check if there's a 'policy' or 'pattern' field directly
        policy = pat.get("policy") or pat.get("pattern") or "star"  # default to star
    
    if policy == "linear":
        return f"((ONCE {interval} A(w,x)) AND B(x,y)) AND (EVENTUALLY {interval} C(y,z))"
    elif policy == "triangle":
        return f"((ONCE {interval} A(x,y)) AND B(y,z)) AND (EVENTUALLY {interval} C(z,x))"
    else:  # star or default
        return f"((ONCE {interval} A(w,x)) AND B(w,y)) AND (EVENTUALLY {interval} C(w,z))"
