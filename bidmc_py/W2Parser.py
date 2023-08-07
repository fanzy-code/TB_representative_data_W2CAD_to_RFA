import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class W2CADMeasurement:
    measurement_number: int = 0
    version: str = ""  # VERSION XX, current version is 02
    date: str = ""  # DATE DD-MM-YYYY
    detector_type: str = ""  # DETY XXX CHA/DIO/DIA  (ionization chamber, semiconductor detector, diamond)
    beam_type: str = ""  # BMTY XXX PHO (High energy photons)
    field_size: str = ""  # FLSZ XXX*XXX in mm
    data_type: str = ""  # TYPE XXX OPD/OPP/WDD/DPR (Open field depth dose curve, open field profile, wedge depth dose curve, diagonal profile), see Eclipse Algorithms Reference for the rest
    axis: str = ""  # AXIS X (X,Y horizonal axes, Z vertical axis (depth), D = diagonal)
    points: str = ""  # PNTS XXX (number of points)
    step: str = ""  # STEP XXX point separation in 1/10 mm
    SSD: str = ""  # SSD XXXX in mm
    depth: str = ""  # DPTH XXX in mm
    data_line: list[str] = field(default_factory=list)  # <SXXX.X SYYY.Y SZZZ.Z SDDD.D>

@dataclass
class W2Parser:
    file_path: Path
    num_scans: int | None = None
    w2cad_measurement_dictionary = {"%VERSION": "version",
                                    "%DATE": "date",
                                    "%DETY": "detector_type",
                                    "%BMTY": "beam_type",
                                    "%FLSZ": "field_size",
                                    "%TYPE": "data_type",
                                    "%AXIS": "axis",
                                    "%PNTS": "points",
                                    "%STEP": "step",
                                    "%SSD": "SSD",
                                    "%DPTH": "depth",
                                    }
    measurement_list: list[W2CADMeasurement] = field(default_factory=list)

    def read_w2(self):
        print(self.w2cad_measurement_dictionary.keys())
        if not str(self.file_path).endswith(".ASC"):
            raise ValueError("File format not supported")
        
        measurement_count = 0
        with open(self.file_path, "r") as fp:
            while True:
                line = fp.readline()

                if line.startswith("$NUMS"):
                    self.num_scans = int(line.split()[-1])
                    continue
                
                # Start of a measurement
                if line.startswith("$STOM"):
                    measurement_count += 1
                    measurement = W2CADMeasurement(measurement_count)
                    continue
                    
                # if line.startswith any of the keys in w2cad_measurement_dictionary
                if any(line.startswith(key) for key in self.w2cad_measurement_dictionary.keys()):
                    key, value = line.split()
                    setattr(measurement, self.w2cad_measurement_dictionary[key], value)
                    continue

                if line.startswith("<"):
                    measurement.data_line.append(line.strip("<>\n"))
                    continue

                # End of a measurement, append to list
                if line.startswith("$ENOM"):
                    self.measurement_list.append(measurement)
                    continue

                # End of file
                if not line:
                    break
        

    def write_to_rfa(self):
        pass


if __name__ == "__main__":
    file_path = Path(__file__).parent.joinpath("6 MV_Open_PDD_sorted.ASC")
    w2file = W2Parser(file_path)
    w2file.read_w2()
    print(w2file)

