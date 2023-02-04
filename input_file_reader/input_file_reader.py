import numpy as np


class InputFileReader:
    def __init__(self):
        self.nodal_data = None
        self.elements = {}
        self.set_data = {'nset': {}, 'elset': {}}

    def read_input_file(self, model_filename, geometry_scale_factor=1.):
        nodes = []
        elements = {}
        with open(model_filename) as full_model_file:
            lines = full_model_file.readlines()
        key_word = None
        key_word_data = None
        continue_line = False
        data = []
        key_word_params = []
        for line in lines:
            if not line.startswith('**') or line:
                if line.startswith('*'):
                    continue_line = False
                    key_word_line = line.split(',')
                    key_word_params = key_word_line[1:]
                    key_word_params = [parameter.lower().rstrip().lstrip() for parameter in key_word_params]
                    key_word = (key_word_line[0][1:]).lower().rstrip()   # Convert to lower case and remove newlines etc
                    key_word_data = [word.strip() for word in key_word_line[1:]]
                else:  # We have a data_row
                    line = ''.join(line.split())    # Removing ALL whitespace
                    data_string = line.split(',')
                    if not continue_line:
                        data = [item.rstrip() for item in data_string]
                    else:
                        data.extend([item.rstrip() for item in data_string])
                    if line.endswith(','):
                        continue_line = True
                        data = data[:-1]            # if the line ends with ',' an extra element is added to data
                    else:
                        continue_line = False

                    if key_word == 'node':
                        nodes.append(data)

                    elif key_word == 'element' and not continue_line:
                        element_type = key_word_data[0][5:].rstrip()
                        if element_type not in elements:
                            elements[element_type] = []
                        elements[element_type].append(data)

                    elif key_word[-3:] == 'set':
                        set_name = key_word_data[0].split('=')[1].rstrip().lower()
                        if set_name not in self.set_data[key_word]:
                            self.set_data[key_word][set_name] = set()
                        if 'generate' in key_word_params:
                            start, stop, step = [int(val) for val in data_string]
                            self.set_data[key_word][set_name].update(range(start, stop, step))
                        else:
                            self.set_data[key_word][set_name].update(int(label) for label in data if label)
                        data = []

        self.nodal_data = np.zeros((len(nodes), len(nodes[0])))

        for i, node in enumerate(nodes):
            self.nodal_data[i, :] = node

        for element_type, data in elements.items():
            self.elements[element_type] = np.array(data, dtype=int)

        if geometry_scale_factor != 1.:
            self.nodal_data[:, 1:] *= geometry_scale_factor

    def write_geom_include_file(self, filename, simulation_type='Mechanical'):
        file_lines = ['*node, nset=all_nodes']
        for node in self.nodal_data:
            node_string = '\t' + str(int(node[0])) + ', '
            for n_data in node[1:]:
                node_string = node_string + str(n_data) + ', '
            file_lines.append(node_string[:-2])
        for element_type, element_data in self.elements.items():
            if element_type[-1].isalpha():
                element_type = element_type[:-1]
            e_type = element_type
            if simulation_type != 'Mechanical':
                if element_type[1] == 'P':
                    e_type = 'DC2D' + element_type[3:]
                elif element_type[1] == 'A':
                    e_type = 'DCAX' + element_type[3:]
                else:
                    e_type = 'DC3D' + element_type[3:]
            file_lines.append('*element, type=' + e_type + ', elset=all_elements', )
            for element in element_data:
                element_string = [str(e) for e in element]
                element_string = ', '.join(element_string)
                file_lines.append('\t' + element_string)

        with open(filename, 'w') as inc_file:
            for line in file_lines:
                inc_file.write(line.lower() + '\n')
            inc_file.write('**EOF')

    def write_sets_file(self, filename, skip_prefix='_', str_to_remove_from_setname='',
                        surfaces_from_element_sets=None):
        file_lines = []

        def check_surface_id(indices, connectivity, surface_nodes):
            for idx in indices:
                if connectivity[idx] not in surface_nodes:
                    return False
            return True

        element_surfaces = {}
        if surfaces_from_element_sets:
            for name in surfaces_from_element_sets:
                name = name.lower()
                surface_elements = self.set_data['elset'][name + '_elements']
                surface_nodes = set(self.set_data['nset'][name + '_nodes'])
                element_surfaces[name] = ([], [], [], [], [], [])
                elements = {}
                for element_type, element_data in self.elements.items():
                    elements[element_type] = dict(zip(element_data[:, 0], element_data[:, 1:]))
                for element in surface_elements:
                    dimensionality = None
                    nodes = None
                    conn = None
                    surface_nodes_lists = None
                    for element_type, element_data in elements.items():
                        if element in element_data:
                            dimensionality = element_type[1]
                            for i in range(len(element_type[3:])):
                                node_str = element_type[3:4+i]
                                try:
                                    nodes = int(node_str)
                                except ValueError:
                                    break
                            conn = element_data[element]

                            break
                    # This handles the case that an element label is in the set but not in the model
                    if dimensionality is not None:
                        if dimensionality in ['A', '2'] and nodes == 4:
                            surface_nodes_lists = [[0, 1], [1, 2], [2, 3], [3, 0]]
                        if dimensionality == '3':
                            print(nodes)
                            if nodes == 8:
                                surface_nodes_lists = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 4, 5],
                                                      [1, 2, 5, 6], [2, 3, 6, 7], [0, 3, 4, 7]]
                            if nodes == 4:
                                surface_nodes_lists = [[0, 1, 2], [0, 1, 3], [1, 2, 3], [0, 2, 3]]
                            if nodes == 6:
                                surface_nodes_lists = [[0, 1, 2], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [0, 2, 5, 3]]
                            if nodes == 10:
                                surface_nodes_lists = [[0, 1, 2, 4, 5, 6], [0, 1, 3, 4, 8, 7],
                                                       [1, 2, 3, 5, 9, 8], [0, 2, 3, 6, 9, 7]]
                        for i, surface_node_order in enumerate(surface_nodes_lists):
                            if check_surface_id(surface_node_order, conn, surface_nodes):
                                element_surfaces[name][i].append(element)
                for i, element_surface in enumerate(element_surfaces[name]):
                    if element_surface:
                        self.set_data['elset'][name + '_elements_' + str(i+1)] = element_surface

        def write_set_rows(data_to_write):
            data_line = '\t'
            counter = 0
            for item in data_to_write:
                data_line += str(int(item)) + ', '
                counter += 1
                if counter == 16 or item == data_to_write[-1]:
                    file_lines.append(data_line[:-2])
                    counter = 0
                    data_line = '\t'

        for set_type, set_data in self.set_data.items():
            for key, data in set_data.items():
                key = key.lower().replace(str_to_remove_from_setname.lower(), '')
                if not key.startswith(skip_prefix) and (key.lower() not in ['all_elements', 'all_nodes']):
                    file_lines.append(('*' + set_type + ', ' + set_type + '=' + key))
                    write_set_rows(sorted(list(data)))

        if surfaces_from_element_sets:
            for name in surfaces_from_element_sets:
                name = name.lower()
                for i, element_surface in enumerate(element_surfaces[name], 1):
                    if element_surface:
                        file_lines.append('*surface, type=element, name=' + name + '_surface_' + str(i))
                        file_lines.append('\t' + name + '_elements_' + str(i) + ', s' + str(i))

                file_lines.append('*surface, type=element, name=' + name + '_surface')
                for i, element_surface in enumerate(element_surfaces[name], 1):
                    if element_surface:
                        file_lines.append('\t' + name + '_elements_' + str(i) + ', s' + str(i))

        with open(filename, 'w') as set_file:
            for line in file_lines:
                set_file.write(line + '\n')
            set_file.write('**EOF')

    def create_node_set(self, name, node_numbers):
        self.set_data['nset'][name] = node_numbers

    def create_element_set(self, name, element_numbers):
        self.set_data['elset'][name] = element_numbers

    def renumber_nodes_and_elements(self):
        node_labels = {n: i for i, n in enumerate(self.nodal_data[:, 0], 1)}
        self.nodal_data[:, 0] = list(node_labels.values())
        element_labels = {}
        element_counter = 1
        for element_data in self.elements.values():
            for e in element_data:
                element_labels[e[0]] = element_counter
                e[0] = element_counter
                element_counter += 1
                for j, n in enumerate(e[1:], 1):
                    e[j] = node_labels[n]

        for set_type, label_dict in zip(['nset', 'elset'], [node_labels, element_labels]):
            for set_data in self.set_data[set_type].values():
                for i, label in enumerate(set_data):
                    set_data[i] = label_dict[label]

    def remove_nodes(self, nodes_to_include):
        # Find the elements corresponding to the model nodes
        nodal_id_set = set(nodes_to_include)
        element_id_set = set()
        new_element_data = []

        for e_type, element_data in self.elements.items():
            for element in element_data:
                include = True
                for node in element[1:]:
                    if int(node) not in nodal_id_set:
                        include = False
                if include:
                    new_element_data.append([int(e) for e in element])
            self.elements[e_type] = np.array(new_element_data, dtype=int)
            element_id_set.update(self.elements[e_type][:, 0])
        for set_type, label_set in zip(['nset', 'elset'], [nodal_id_set, element_id_set]):
            for set_name, set_data in self.set_data[set_type].items():
                new_set_data = []
                for label in set_data:
                    if label in label_set:
                        new_set_data.append(label)
                self.set_data[set_type][set_name] = new_set_data
