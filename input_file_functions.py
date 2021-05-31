def mirror_model(input_file_reader, axis):
    input_file_reader.nodal_data[:, 2] *= -1
    for element_type, element_data in input_file_reader.elements.items():
        new_elements = np.copy(element_data)
        if axis == "x":
            new_elements[:, 1], new_elements[:, 2] = element_data[:, 2], element_data[:, 1]
            new_elements[:, 3], new_elements[:, 4] = element_data[:, 4], element_data[:, 3]
            new_elements[:, 5], new_elements[:, 6] = element_data[:, 6], element_data[:, 5]
            new_elements[:, 7], new_elements[:, 8] = element_data[:, 8], element_data[:, 7]

        elif axis == "y":
            new_elements[:, 1], new_elements[:, 4] = element_data[:, 4], element_data[:, 1]
            new_elements[:, 2], new_elements[:, 3] = element_data[:, 3], element_data[:, 2]
            new_elements[:, 5], new_elements[:, 8] = element_data[:, 8], element_data[:, 5]
            new_elements[:, 6], new_elements[:, 7] = element_data[:, 7], element_data[:, 6]

        elif axis == "z":
            new_elements[:, 1] = new_elements[:, 5] = element_data[:, 5], element_data[:, 1]
            new_elements[:, 2] = new_elements[:, 6] = element_data[:, 6], element_data[:, 2]
            new_elements[:, 3] = new_elements[:, 7] = element_data[:, 7], element_data[:, 3]
            new_elements[:, 4] = new_elements[:, 8] = element_data[:, 8], element_data[:, 4]

        else:
            raise ValueError("Invalid axis argument")
        input_file_reader.elements[element_type] = new_elements
