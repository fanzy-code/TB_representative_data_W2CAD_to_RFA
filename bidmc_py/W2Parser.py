import re
import textwrap
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

    # Translation dictionary for the w2cad file format
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
    
    
    def __repr__(self):
       string_representation = f"Measurement number {self.measurement_number}"
       return string_representation

    def write_rfa300_datablock(self):

        # Scan Type, SCN
        scan_type_mapping = {"OPD": "DPT", "OPP": "PRO", "WDD": "DPT", "DPR": "DIA"} 
        rfa_scantype = scan_type_mapping[self.data_type]

        # Detector Type, FLD
        detector_type_mapping = {"CHA": "ION", "DIO": "SEM"} # Diamond/Undefined not supported
        rfa_detector_type = detector_type_mapping[self.detector_type]        

        # Date, DAT
        day, month, year = self.date.split("-")
        rfa300_date = f"{month}-{day}-{year}"

        # Field Size, FSZ - check the tab
        x, y = self.field_size.split('*')
        rfa300_fsz = f"{x}\t{y}"

        # Beam type, BMT
        beam_type_mapping = {"PHO": "PHO"}
        rfa_beam_type = beam_type_mapping[self.beam_type]
        rfa_energy = "placeholder" # Read the energy from somewhere
        rfa300_bmt = f"{rfa_beam_type}\t{rfa_energy}"

        # SSD
        rfa_ssd = self.SSD

        # Beam reference distance, BRD
        rfa_brd = self.SSD

        # Measurement type, MEA
        measurement_type_mapping = {"OPD": "1", "OPP": "2", "WDD": "5", "WDP": "6"} 
        rfa_mea = measurement_type_mapping[self.data_type]

        # Profile depth, PRD
        rfa_prd = self.depth

        # Number of points, PTS
        rfa_pts = self.points

        header = textwrap.dedent(f"""
        #
        # RFA300 ASCII Measurement Dump ( BDS format )
        #
        # Measurement number 	{self.measurement_number}
        #
        %VNR 1.0
        %MOD 	RAT
        %TYP 	SCN 
        %SCN 	{rfa_scantype} 
        %FLD 	ION 
        %DAT 	11-25-2008 
        %TIM 	19:17:19 
        %FSZ 	100	100
        %BMT 	PHO	   15.0
        %SSD 	1000
        %BUP 	0
        %BRD 	1000
        %FSH 	-1
        %ASC 	0
        %WEG 	0
        %GPO 	0
        %CPO 	0
        %MEA 	2
        %PRD 	300,00003427124
        %PTS 	349
        %STS 	    0.0	  -71.5	   30.0 # Start Scan values in mm ( X , Y , Z )
        %EDS 	    0.0	   71.2	   30.1 # End Scan values in mm ( X , Y , Z )
        """).strip()

@dataclass
class W2Parser:
    file_path: Path
    num_scans: int | None = None
    measurement_list: list[W2CADMeasurement] = field(default_factory=list)

    def read_w2(self):
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
                if any(line.startswith(key) for key in measurement.w2cad_measurement_dictionary.keys()):
                    key, value = line.split()
                    setattr(measurement, measurement.w2cad_measurement_dictionary[key], value)
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
        
    def write_rfa300_header(self):
        # Header block for RFA300
        rfa300_header = textwrap.dedent(f"""
        :MSR 	{self.num_scans}	 # No. of measurement in file
        :SYS BDS 0   # Beam Data Scanner System
        """).strip()
        return rfa300_header

if __name__ == "__main__":
    file_path = Path(__file__).parent.joinpath("6 MV_Open_PDD_sorted.ASC")
    w2file = W2Parser(file_path)
    w2file.read_w2()

