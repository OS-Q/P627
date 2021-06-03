
from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = "opencpu"
module = platform + "-" + env.BoardConfig().get("build.core")
m = __import__(module)
globals()[module] = m
m.dev_init(env, platform)
#print( env.Dump() )






