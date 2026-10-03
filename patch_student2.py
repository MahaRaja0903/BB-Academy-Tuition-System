with open("bb_tution_management/bb_academy/doctype/student/student.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = 0
for i, line in enumerate(lines):
    if skip > 0:
        skip -= 1
        continue
    if "def set_preferred_whatsapp_number(self):" in line:
        new_lines.append(line)
        new_lines.append('\t\tif self.preferred_mobile_number == "Father":\n')
        new_lines.append('\t\t\tphone = self.father_mobile_number\n')
        new_lines.append('\t\telif self.preferred_mobile_number == "Mother":\n')
        new_lines.append('\t\t\tphone = self.mother_mobile_number\n')
        new_lines.append('\t\telif self.preferred_mobile_number == "Guardian":\n')
        new_lines.append('\t\t\tphone = self.guardian_mobile_number\n')
        new_lines.append('\t\telse:\n')
        new_lines.append('\t\t\tphone = self.father_mobile_number or self.mother_mobile_number or self.guardian_mobile_number\n')
        
        # We need to skip the original lines
        # Original lines were:
        # if self.preferred_mobile_number == "Father":
        # 	phone = self.father_mobile_number
        # elif self.preferred_mobile_number == "Mother":
        # 	phone = self.mother_mobile_number
        # elif self.preferred_mobile_number == "Guardian":
        # 	phone = self.guardian_mobile_number
        # else:
        # 	phone = self.father_mobile_number or self.mother_mobile_number or self.guardian_mobile_number
        # 	phone = self.father_mobile_number or self.mother_mobile_number
        
        # we can just keep skipping until we hit `if phone:`
        j = 1
        while "if phone:" not in lines[i+j] and i+j < len(lines):
            j += 1
            skip = j - 1
            
        continue
        
    new_lines.append(line)

with open("bb_tution_management/bb_academy/doctype/student/student.py", "w") as f:
    f.writelines(new_lines)
