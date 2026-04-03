from siliconcompiler import ASIC, Design
from siliconcompiler.targets import skywater130_demo

def main():
    design = Design("tiny_tpu")
    design.set_topmodule("tpu", fileset="rtl")

    design.add_file("hdl/tpu.sv", fileset="rtl")
    design.add_file("hdl/scratchpad.sv", fileset="rtl")
    design.add_file("hdl/metadata_regs.sv", fileset="rtl")
    design.add_file("hdl/systolic_array.sv", fileset="rtl")
    design.add_file("hdl/mac.sv", fileset="rtl")
    design.add_file("pkg/types.sv", fileset="rtl")
    design.add_file("constraints/tpu.sdc", fileset="sdc")

    project = ASIC(design)
    project.add_fileset(["rtl", "sdc"])

    skywater130_demo(project)

    project.option.set_remote(True)

    project.run()
    project.summary()
    # project.show()


if __name__ == "__main__":
    main()