#  This work is based on original code developed and copyrighted by TNO 2022.
#  Subsequent contributions are licensed to you by the developers of such code and are
#  made available to the Project under one or several contributor license agreements.
#
#  This work is licensed to you under the Apache License, Version 2.0.
#  You may obtain a copy of the license at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Contributors:
#      TNO         - Initial implementation
#  Manager:
#      TNO

import math
import uuid
from typing import Dict
import esdl
import re

from RDWGSConverter import RDWGSConverter


class Item:
    def __init__(self, lines):
        self.lines = lines
        self.id = lines[0].split(' ')[1]        # ID is mostly the second element in the #1 line, else overwrite...
        self.naam = ""
        self.esdl = None

    def generate_point(self, gx, gy):
        rd_wgs_conv = RDWGSConverter()
        loc = rd_wgs_conv.fromRdToWgs([float(gx), float(gy)])
        point = esdl.Point(lat=loc[0], lon=loc[1], CRS="WGS84")
        return point

    def generate_line(self, punten):
        line = esdl.Line()
        for p in punten:
            line.point.append(self.generate_point(p[0], p[1]))
        return line

    @staticmethod
    def parse_GNF(state, idx, gnf_lines):
        if gnf_lines[idx][0:3] != '#1 ':
            print("Error in implementation, new Item instantiated at the wrong line, number", idx)
            exit()

        lines = list()
        while True:
            if gnf_lines[idx][0:3] in ['#1 ', '#6 ', '#9 ']:
                lines.append(gnf_lines[idx])
            idx += 1
            if gnf_lines[idx][0:3] == '#1 ' or gnf_lines[idx][0:2] == '[]':
                break

        if state == "NODE":
            return Node(lines)
        elif state == "PROFILE":
            return Profile(lines)
        elif state == "LINK":
            return Link(lines)
        elif state == "CABLE":
            return Cable(lines)
        elif state == "TRANSFORMER":
            return Transformer(lines)
        elif state == "SOURCE":
            return Source(lines)
        elif state == "HOME":
            return Home(lines)

    def generate_ESDL(self, item_dict):
        pass


class ItemDict:
    def __init__(self):
        self.item_dict: Dict[str, Dict[str, Item]] = {
            "Node": {},
            "Profile": {},
            "Link": {},
            "Cable": {},
            "Transformer": {},
            "Source": {},
            "Home": {},
        }

    def add(self, item: Item):
        self.item_dict[item.__class__.__name__][item.id] = item

    def generate_assets(self, es):
        area = es.instance[0].area
        for category, items in self.item_dict.items():
            for item_id, item in items.items():
                esdl_item = item.generate_ESDL(self.item_dict)
                if esdl_item:
                    area.asset.append(esdl_item)
                else:
                    print("esdl_item could not be generated", category, item_id)

    def generate_connections(self):
        for key in ['Home', 'Cable', 'Source', 'Transformer', 'Link']:
            for item_id, item in self.item_dict[key].items():
                item.connect(self.item_dict)


class Node(Item):
    def __init__(self, lines):
        Item.__init__(self, lines)
        self.gx = 0
        self.gy = 0
        self.process_lines()

    def process_lines(self):
        try:
            PATTERN = re.compile(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''')
            [line_id, nr, revision, naam, kortenaam, ID, Unom, g, aardingsconfiguratie, s_n_pe, s_pe_a, Ra, k_h1, k_h2,
                k_h3, k_h4, s_h1, s_h2, s_h3, s_h4, gx, gy, nietberekenen    #, faalfrequentie
            ] = PATTERN.split(self.lines[0])[1::2]

            # print(nr, gx, gy)
            self.gx = float(gx)
            self.gy = float(gy)
            self.naam = naam

        except ValueError:
            print("-- EXCEPTION: id len ->", self.id, len(self.lines[0].split(' ')))

    def generate_geometry(self):
        return self.generate_point(self.gx, self.gy)

    def generate_ESDL(self, item_dict):
        joint = esdl.Joint(id=str(uuid.uuid4()), name=self.naam, originalIdInSource=self.id)
        joint.geometry = self.generate_geometry()
        joint.port.append(esdl.InPort(id=str(uuid.uuid4()), name="In"))
        joint.port.append(esdl.OutPort(id=str(uuid.uuid4()), name="Out"))
        self.esdl = joint
        return joint


class Profile(Item):
    def __init__(self, lines):
        Item.__init__(self, lines)
        self.process_lines()

    def process_lines(self):
        try:
            PATTERN = re.compile(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''')
            [line_id,
             ] = PATTERN.split(self.lines[0])[1::2]

        except ValueError:
            print("-- EXCEPTION: id len ->", self.id, len(self.lines[0].split(' ')))

    def generate_ESDL(self, item_dict):
        pass


class Link(Item):
    def __init__(self, lines):
        Item.__init__(self, lines)
        self.knr1 = None
        self.knr2 = None
        self.punten = list()
        self.process_lines()

    def process_lines(self):
        try:
            PATTERN = re.compile(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''')
            [line_id, nr, revision, knr1, knr2, naam, s1_l1, s1_l2, s1_l3, s1_n, s1_pe, s2_l1, s2_l2, s2_l3, s2_n,
             s2_pe, veld1, veld2, faalfrequentie, s1_h1, s1_h2, s1_h3, s1_h4, s2_h1, s2_h2, s2_h3, s2_h4] = \
                PATTERN.split(self.lines[0])[1::2]

            self.naam = naam
            self.knr1 = knr1
            self.knr2 = knr2

        except ValueError:
            print("-- EXCEPTION: id len ->", self.id, len(self.lines[0].split(' ')))

    def generate_ESDL(self, item_dict):
        # For now assume that the two 'knooppunten' are always at same location
        node1 = item_dict['Node'][self.knr1]

        cable = esdl.ElectricityCable(id=str(uuid.uuid4()), name=self.naam, originalIdInSource=self.id)
        cable.geometry = node1.generate_geometry()
        cable.port.append(esdl.InPort(id=str(uuid.uuid4()), name="In"))
        cable.port.append(esdl.OutPort(id=str(uuid.uuid4()), name="Out"))
        self.esdl = cable
        return cable

    def connect(self, item_dict):
        self.esdl.port[0].connectedTo.append(item_dict['Node'][self.knr1].esdl.port[1])
        self.esdl.port[1].connectedTo.append(item_dict['Node'][self.knr2].esdl.port[0])


class Cable(Item):
    def __init__(self, lines):
        Item.__init__(self, lines)
        self.knr1 = None
        self.knr2 = None
        self.punten = list()
        self.process_lines()

    def process_lines(self):
        try:
            PATTERN = re.compile(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''')
            [line_id, nr, revision, knr1, knr2, naam, s1_l1, s1_l2, s1_l3, s1_n, s1_pe, s2_l1, s2_l2, s2_l3, s2_n,
             s2_pe, veld1, veld2, faalfrequentie, nieuw, woningaarding, woningRa, PV_schaling, PV_profielnr, k1_1, k1_2,
             k1_3, k1_4, k1_5, k1_6, k1_7, k1_8, k1_9, k2_1, k2_2, k2_3, k2_4, k2_5, k2_6, k2_7, k2_8, k2_9, s1_h1,
             s1_h2, s1_h3, s1_h4, s2_h1, s2_h2, s2_h3, s2_h4, smeltveiligheidtype1_h, stroomtype1_h,
             smeltveiligheidtype2_h, stroomtype2_h
             ] = PATTERN.split(self.lines[0])[1::2]

            self.naam = naam
            self.knr1 = knr1
            self.knr2 = knr2

            line6 = PATTERN.split(self.lines[1])[1::2]
            if line6[0] == '#6':
                del line6[0]  # remove 1st element (The "#6" before all coordinates)
                coords = [float(c) for c in line6]
                self.punten = list(zip(*(iter(coords),) * 2))
            else:
                raise Exception("2nd line is not of type #6, improve algorithm")

        except ValueError:
            print("-- EXCEPTION: id len ->", self.id, len(self.lines[0].split(' ')))

    def generate_geometry(self):
        return self.generate_line(self.punten)

    def generate_ESDL(self, item_dict):
        cable = esdl.ElectricityCable(id=str(uuid.uuid4()), name=self.naam, originalIdInSource=self.id)
        cable.geometry = self.generate_geometry()
        cable.port.append(esdl.InPort(id=str(uuid.uuid4()), name="In"))
        cable.port.append(esdl.OutPort(id=str(uuid.uuid4()), name="Out"))
        self.esdl = cable
        return cable

    @staticmethod
    def distance(node, cable_point):
        return math.sqrt((node.gx - cable_point[0])**2 + (node.gy - cable_point[1])**2)

    def connect(self, item_dict):
        node1 = item_dict['Node'][self.knr1]
        node2 = item_dict['Node'][self.knr2]

        if Cable.distance(node1, self.punten[0]) < Cable.distance(node2, self.punten[0]):
            self.esdl.port[0].connectedTo.append(item_dict['Node'][self.knr1].esdl.port[1])
            self.esdl.port[1].connectedTo.append(item_dict['Node'][self.knr2].esdl.port[0])
        else:
            self.esdl.port[0].connectedTo.append(item_dict['Node'][self.knr2].esdl.port[1])
            self.esdl.port[1].connectedTo.append(item_dict['Node'][self.knr1].esdl.port[0])


class Transformer(Item):
    def __init__(self, lines):
        Item.__init__(self, lines)
        self.knr1 = None
        self.knr2 = None
        self.bladnr = None
        self.process_lines()

    def process_lines(self):
        try:
            PATTERN = re.compile(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''')
            # 1 extra parameter in input data --> xxx
            [line_id, nr, revision, knr1, knr2, naam, s1_l1, s1_l2, s1_l3, s1_n, s1_pe, s2_l1, s2_l2, s2_l3, s2_n,
             s2_pe, veld1, veld2, faalfrequentie, trafotype, s_n_pe, s_pe_a, Ra, trapstand, regelingstatus, meetzijde,
             regelknoopnr, Uset, Uband, regelingsoort, Rc, Xc, terugc, Pmin, Umin, Pmax, Umax, xxx
            ] = PATTERN.split(self.lines[0])[1::2]

            self.naam = naam
            self.knr1 = knr1
            self.knr2 = knr2

            line9 = PATTERN.split(self.lines[1])[1::2]
            self.bladnr = int(line9[1])

        except ValueError:
            print("-- EXCEPTION: id len ->", self.id, len(self.lines[0].split(' ')))

    def generate_ESDL(self, item_dict):
        # For now assume that the two 'knooppunten' are always at same location
        node1 = item_dict['Node'][self.knr1]
        transformer = esdl.Transformer(id=str(uuid.uuid4()), name=self.naam, originalIdInSource=self.id)
        transformer.geometry = node1.generate_geometry()
        transformer.port.append(esdl.InPort(id=str(uuid.uuid4()), name="In"))
        transformer.port.append(esdl.OutPort(id=str(uuid.uuid4()), name="Out"))
        self.esdl = transformer
        return transformer

    def connect(self, item_dict):
        self.esdl.port[0].connectedTo.append(item_dict['Node'][self.knr1].esdl.port[1])
        self.esdl.port[1].connectedTo.append(item_dict['Node'][self.knr2].esdl.port[0])


class Source(Item):
    def __init__(self, lines):
        Item.__init__(self, lines)
        self.gx = None
        self.gy = None
        self.knr = None
        self.profielnr = None
        self.bladnr = None
        self.process_lines()

    def process_lines(self):
        try:
            PATTERN = re.compile(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''')
            [line_id, knr, subnr, revision, naam, s_l1, s_l2, s_l3, s_n, veld, Umin, Umax, Uprofiel, Sk2nom, profielnr,
             faalfrequentie] = PATTERN.split(self.lines[0])[1::2]

            self.id = subnr
            self.knr = knr
            self.naam = naam
            self.profielnr = profielnr

            [line_id, bladnr, x, y, kleur, grootte, dikte, stijl, tekstkleur, tekstgrootte, lettertype, tekststijl,
             geentekst, opdekop, fsx, fsy, sx, sy, nx, ny, vo] = PATTERN.split(self.lines[1])[1::2]

            self.bladnr = int(bladnr)
            self.gx = float(x)
            self.gy = float(y)

        except ValueError:
            print("-- EXCEPTION: id len ->", self.id, len(self.lines[0].split(' ')))

    def generate_ESDL(self, item_dict):
        node = item_dict['Node'][self.knr]
        source = esdl.Import(id=str(uuid.uuid4()), name=self.naam, originalIdInSource=self.id)
        source.geometry = node.generate_geometry()
        source.port.append(esdl.OutPort(id=str(uuid.uuid4()), name="Out"))
        self.esdl = source
        return source

    def connect(self, item_dict):
        self.esdl.port[0].connectedTo.append(item_dict['Node'][self.knr].esdl.port[0])


class Home(Item):
    def __init__(self, lines):
        Item.__init__(self, lines)
        self.gx = 0
        self.gy = 0
        self.knr = None
        self.process_lines()

    def process_lines(self):
        try:
            PATTERN = re.compile(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''')
            [line_id, knr, subnr, revision, naam, s_l1, s_l2, s_l3, s_n, veld, s_pe, k_1, k_2, k_3, lengte, kabeltype,
             aardingsconfiguratie, sh_n_pe, sh_pe_pe, sh_pe_a, Ra, sh_h, smeltveiligheidtype, stroomtype, fasen, soort,
             aansluitwaarde, Iaardlek, risico, gx, gy, adres, postcode, woonplaats
             ] = PATTERN.split(self.lines[0])[1::2]

            self.gx = float(gx)
            self.gy = float(gy)
            self.naam = naam
            self.id = knr + '_' + subnr
            self.knr = knr
        except ValueError:
            print("-- EXCEPTION: id len ->", self.id, len(self.lines[0].split(' ')))
        except:
            print("-- OTHER EXCEPTION")

    def generate_geometry(self):
        return self.generate_point(self.gx, self.gy)

    def generate_ESDL(self, item_dict):
        home = esdl.ElectricityDemand(id=str(uuid.uuid4()), name=self.naam, originalIdInSource=self.id)
        home.geometry = self.generate_geometry()
        home.port.append(esdl.InPort(id=str(uuid.uuid4()), name="In"))
        self.esdl = home
        return home

    def connect(self, item_dict):
        self.esdl.port[0].connectedTo.append(item_dict['Node'][self.knr].esdl.port[1])

