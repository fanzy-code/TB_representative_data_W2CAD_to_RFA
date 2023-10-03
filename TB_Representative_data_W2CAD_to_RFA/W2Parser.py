import os, sys
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.getcwd())
from definitions import ROOT_DIR


@dataclass
class W2CADMeasurement:
    ### See Eclipse Algorithms Reference guide Appendix C for w2CAD file format documentation

    measurement_number: int = 0
    energy: int = 0  # Read from the file name

    # Measurement header information
    date: str = ""  # DATE DD-MM-YYYY
    version: str = ""  # VERSION XX, current version is 02
    detector_type: str = (
        ""  # DETY XXX CHA/DIO/DIA  (ionization chamber, semiconductor detector, diamond)
    )
    beam_type: str = ""  # BMTY XXX PHO/ELE (High energy photons, Electron)
    data_type: str = ""  # TYPE XXX OPD/OPP/WDD/WDD_SSD80/WDD_SSD120//WDP/WLP/DPR
    wedge_name: str = "0"  # WDGL XX
    wedge_direction: str = ""  # WDGD X (L,R)
    axis: str = ""  # AXIS X (X,Y horizonal axes, Z vertical axis (depth), D = diagonal)
    points: str = ""  # PNTS XXX (number of points)
    step: str = ""  # STEP XXX point separation in 1/10 mm
    SSD: str = ""  # SSD XXXX in mm
    field_size: str = ""  # FLSZ XXX*XXX in mm
    depth: str = "0"  # DPTH XXX in mm
    data_line: list[str] = field(default_factory=list)  # <SXXX.X SYYY.Y SZZZ.Z SDDD.D>

    # Translation dictionary for the w2cad file format
    w2cad_measurement_dictionary = {
        "%DATE": "date",
        "%VERSION": "version",
        "%DETY": "detector_type",
        "%BMTY": "beam_type",
        "%TYPE": "data_type",
        "%WDGL": "wedge_name",
        "%WDGD": "wedge_direction",
        "%AXIS": "axis",
        "%PNTS": "points",
        "%STEP": "step",
        "%SSD": "SSD",
        "%SPD": "SPD",  # Electrons use SPD instead of SSD
        "%FLSZ": "field_size",
        "%DPTH": "depth",
    }

    def __repr__(self):
        string_representation = (
            f"Measurement number {self.measurement_number} ({self.energy} {self.beam_type})"
        )
        return string_representation

    def write_rfa_datablock(self):
        ### See Technical Note 997-103_TN006_090130, OmniPro-Accept for RFA300 ASCII file format documentation

        # %MOD Mode, support for RAT only
        # %TYP Type, support for SCN only

        # %SCN ScanType, DPT/PRO/DIA (DepthDose, Profile, Diagonal)
        scan_type_mapping = {
            "OPD": "DPT",
            "OPP": "PRO",
            "WDD": "DPT",
            "WDD_SSD80": "DPT",
            "WDD_SSD120": "DPT",
            "WDP": "PRO",
            "WLP": "PRO",
            "DPR": "DIA",
            "BLD": "DPT",
            "MeasuredDepthDosesForApplicator": "DPT",
            "MeasuredDepthDosesForOpenBeam": "DPT",
            "MeasuredProfileForOpenBeam": "PRO",
        }
        rfa_scantype = scan_type_mapping[self.data_type]

        # %FLD DetectorType, ION/SEM/UDF (Ionization chamber, Semiconductor detector, Undefined)
        # diamond detector & undefined not supported
        detector_type_mapping = {"CHA": "ION", "DIO": "SEM"}
        rfa_detector_type = detector_type_mapping[self.detector_type]

        # %DAT DateOfCreation MM-DD-YYYY
        day, month, year = self.date.split("-")
        rfa_date = f"{month}-{day}-{year}"

        # %TIM TimeOfCreation HH:MM:SS

        # %FSZ FieldWidth FieldHieght
        # in mm
        x, y = self.field_size.split("*")
        rfa_fsz = f"{x}\t{y}"

        # %BMT RadType Energy
        beam_type_mapping = {"PHO": "PHO", "ELE": "ELE"}
        rfa_beam_type = beam_type_mapping[self.beam_type]
        rfa_energy = f"{float(self.energy):.1f}"  # energy to 1 decimal place

        # %SSD
        rfa_ssd = self.SSD

        if rfa_ssd == "":  # Electrons use SPD instead of SSD
            rfa_ssd = f"{float(self.SPD)*10:.0f}"

        # %BUP BuildUp

        # $BRD BeamReferenceDist
        rfa_brd = self.SSD

        if rfa_brd == "":  # Electrons use SPD instead of SSD
            rfa_brd = f"{float(self.SPD)*10:.0f}"

        # FSH Shape, 1 supported, rectangular

        # %ASC AccessoryNbr Accessory number

        # %WEG WedgeNbr
        rfa_weg = self.wedge_name

        # %GPO Gantry Angle, 0 supported

        # %CPO CollimatorAngle, 0 supported CollimatorAngle in degrees

        # %MEA MeasurementType
        measurement_type_mapping = {
            "OPD": "1",
            "OPP": "2",
            "WDD": "5",
            "WDD_SSD80": "5",
            "WDD_SSD120": "5",
            "WDP": "6",
            "WLP": "6",
            "BLD": "1",
            "DPR": "2",
            "MeasuredProfileForOpenBeam": "2",
            "MeasuredDepthDosesForApplicator": "1",
            "MeasuredDepthDosesForOpenBeam": "1",
        }
        rfa_mea = measurement_type_mapping[self.data_type]

        # %PRD ProfileDepth
        rfa_prd = f"{float(self.depth):.1f}"
        rfa_prd = rfa_prd.replace(".", ",")

        # %PTS NbrOfPoints
        rfa_pts = self.points

        # %STS StartX StartY StartZ
        starting_point = self.data_line[0]
        # start_x, start_y, start_z, start_dose = starting_point.split(' ')
        start_y, start_x, start_z, start_dose = starting_point.split(
            " "
        )  # X, Y swapped for rfa format
        start_x = f"{float(start_x):.1f}"
        start_y = f"{float(start_y):.1f}"
        start_z = f"{float(start_z):.1f}"

        # %EDS EndX EndY EndZ
        end_point = self.data_line[-1]
        # end_x, end_y, end_z, end_dose = end_point.split(' ')
        end_y, end_x, end_z, end_dose = end_point.split(" ")  # X, Y swapped for rfa format
        end_x = f"{float(end_x):.1f}"
        end_y = f"{float(end_y):.1f}"
        end_z = f"{float(end_z):.1f}"

        scan_header_block = textwrap.dedent(
            f"""
        #
        # RFA300 ASCII Measurement Dump ( BDS format )
        #
        # Measurement number 	{self.measurement_number}
        #
        %VNR 1.0
        %MOD 	RAT
        %TYP 	SCN
        %SCN 	{rfa_scantype}
        %FLD 	{rfa_detector_type}
        %DAT 	{rfa_date}
        %TIM 	12:00:00
        %FSZ 	{rfa_fsz}
        %BMT 	{rfa_beam_type}	   {rfa_energy}
        %SSD 	{rfa_ssd}
        %BUP 	0
        %BRD 	{rfa_brd}
        %FSH 	1
        %ASC 	0
        %WEG 	{rfa_weg}
        %GPO 	0
        %CPO 	0
        %MEA 	{rfa_mea}
        %PRD 	{rfa_prd}
        %PTS 	{rfa_pts}
        %STS 	    {start_x}	  {start_y}	   {start_z} # Start Scan values in mm ( X , Y , Z )
        %EDS 	    {end_x}	   {end_y}	   {end_z} # End Scan values in mm ( X , Y , Z )
        """
        ).strip()

        scan_data_block = textwrap.dedent(
            f"""                                   
        #
        #	  X      Y      Z     Dose
        #
        """
        ).strip()

        scan_data_block += "\n"

        for line in self.data_line:
            # x, y, z, dose = line.split(' ')
            y, x, z, dose = line.split(" ")  # X, Y swapped
            x = f"{float(x):.1f}"
            y = f"{float(y):.1f}"
            z = f"{float(z):.1f}"
            dose = f"{float(dose):.1f}"
            scan_data_block += f"=\t{x}\t{y}\t{z}\t{dose}\n"

        scan_data_block += ":EOM # End of Measurement\n"

        return scan_header_block + "\n" + scan_data_block


@dataclass
class W2Parser:
    file_path: Path
    num_scans: int | None = None
    measurement_list: list[W2CADMeasurement] = field(default_factory=list)

    def read_w2(self):
        if not str(self.file_path).endswith(".ASC"):
            raise ValueError("File format not supported")

        measurement_count = 0
        energy_match = re.search(r"(\d+)\s*(?:MeV|MV|X)", self.file_path.name)
        if energy_match:
            energy = energy_match.group(1)

        else:
            # Energy is not found in filename, search the file path
            energy_match = re.search(r"(\d+)X", str(self.file_path))
            energy = energy_match.group(1)

        with open(self.file_path, "r") as fp:
            while True:
                line = fp.readline()

                if line.startswith("$NUMS"):
                    self.num_scans = int(line.split()[-1])
                    continue

                # Start of a measurement
                if line.startswith("$STOM"):
                    measurement_count += 1
                    measurement = W2CADMeasurement(measurement_count, energy)
                    continue

                # if line.startswith any of the keys in w2cad_measurement_dictionary``
                if any(
                    line.startswith(key) for key in measurement.w2cad_measurement_dictionary.keys()
                ):
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

    def write_rfa_header(self):
        # Header block for RFA300
        rfa300_header = textwrap.dedent(
            f"""
        :MSR 	{self.num_scans}	 # No. of measurement in file
        :SYS BDS 0   # Beam Data Scanner System
        """
        ).strip()
        return rfa300_header

    def write_rfa_measurements(self):
        rfa_measurements = ""
        for measurement in self.measurement_list:
            rfa_measurements += measurement.write_rfa_datablock()
        return rfa_measurements

    def write_rfa_footer(self):
        rfa300_footer = textwrap.dedent(
            f"""
        :EOF # End of File
        """
        ).strip()
        return rfa300_footer

    def write_rfa_file(self, output_path):
        rfa_header = self.write_rfa_header()
        rfa_measurements = self.write_rfa_measurements()
        rfa_footer = self.write_rfa_footer()

        rfa_file = rfa_header + "\n" + rfa_measurements + "\n" + rfa_footer

        # rfa_filename = self.file_path.stem + "_rfa.ASC"
        # rfa_filepath = output_path / rfa_filename
        with open(output_path, "w") as fp:
            fp.write(rfa_file)

        return rfa_file


def process_files(input_dir, output_dir):
    for root, _, files in os.walk(input_dir):
        for file in files:
            print(f"Processing {file}")
            if file.lower().endswith(".asc"):
                input_filepath = Path(root) / file
                output_filepath = (
                    Path(output_dir)
                    / Path(root).relative_to(input_dir)
                    / (Path(file).stem + "_rfa.ASC")
                )

                w2file = W2Parser(input_filepath)
                w2file.read_w2()
                print(f"Writing file: {output_filepath}")
                w2file.write_rfa_file(output_filepath)


if __name__ == "__main__":
    print("Converting W2CAD files to RFA300 format...")
    results_directory = Path(ROOT_DIR).joinpath("rfa_W2CAD/")
    varian_w2cad_directory = Path(ROOT_DIR).joinpath(
        "references/TB_RepresentativeData_Eclipse/W2CAD/"
    )

    # Make all the subdirectories in the results directory
    for sub_dir in varian_w2cad_directory.glob("**/"):
        if sub_dir.is_dir():
            output_dir = results_directory / sub_dir.relative_to(varian_w2cad_directory)
            output_dir.mkdir(parents=True, exist_ok=True)

    # Process all the files
    process_files(varian_w2cad_directory, results_directory)
