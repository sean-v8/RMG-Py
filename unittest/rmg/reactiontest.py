#!/usr/bin/python
# -*- coding: utf-8 -*-
 
import unittest

import sys
sys.path.append('.')

import rmg.thermo.model as thermo
from rmg.structure import Structure
from rmg.species import makeNewSpecies
import rmg.reaction as reaction
from rmg.kinetics.data import ReactionFamilySet
	
################################################################################

class ReactionCheck(unittest.TestCase):                          

	def testMakeNewReaction(self):
		"""Create a new reaction and check you can identify the reverse"""
		structure1 = Structure()
		structure1.fromAdjacencyList("""
		1 C 0 {2,D} {7,S} {8,S}
		2 C 0 {1,D} {3,S} {9,S}
		3 C 0 {2,S} {4,D} {10,S}
		4 C 0 {3,D} {5,S} {11,S}
		5 *1 C 0 {4,S} {6,S} {12,S} {13,S}
		6 C 0 {5,S} {14,S} {15,S} {16,S}
		7 H 0 {1,S}
		8 H 0 {1,S}
		9 H 0 {2,S}
		10 H 0 {3,S}
		11 H 0 {4,S}
		12 *2 H 0 {5,S}
		13 H 0 {5,S}
		14 H 0 {6,S}
		15 H 0 {6,S}
		16 H 0 {6,S}
		""")
		
		structure2 = Structure()
		structure2.fromAdjacencyList("""
		1 *3 H 1
		""")
		
		structure3 = Structure()
		structure3.fromAdjacencyList("""
		1 C 0 {2,D} {7,S} {8,S}
		2 C 0 {1,D} {3,S} {9,S}
		3 C 0 {2,S} {4,D} {10,S}
		4 C 0 {3,D} {5,S} {11,S}
		5 *3 C 1 {4,S} {6,S} {12,S}
		6 C 0 {5,S} {13,S} {14,S} {15,S}
		7 H 0 {1,S}
		8 H 0 {1,S}
		9 H 0 {2,S}
		10 H 0 {3,S}
		11 H 0 {4,S}
		12 H 0 {5,S}
		13 H 0 {6,S}
		14 H 0 {6,S}
		15 H 0 {6,S}
		""")
		
		structure4 = Structure()
		structure4.fromAdjacencyList("""
		1 *1 H 0 {2,S}
		2 *2 H 0 {1,S}
		""")
		
		C6H10, isNew = makeNewSpecies(structure1)
		H, isNew = makeNewSpecies(structure2)
		C6H9, isNew = makeNewSpecies(structure3)
		H2, isNew = makeNewSpecies(structure4)
		
		# wipe the reaction list
		reaction.reactionDict={}
		
		reaction1, isNew = makeNewReaction([C6H9, H2], [C6H10, H], \
			[C6H9.structure[0], H2.structure[0]], \
			[C6H10.structure[0], H.structure[0]], \
			None)
		self.assertFalse(reaction1 is None)
		self.assertTrue(isNew)
		
		reaction2, isNew = makeNewReaction([C6H10, H], [C6H9, H2], \
			[C6H10.structure[0], H.structure[0]], \
			[C6H9.structure[0], H2.structure[0]], \
			None)
		
		self.assertTrue(reaction1 is reaction2)
		self.assertFalse(isNew)
		
		
class ReactionSetCheck(unittest.TestCase): 
	
	def loadDatabase(self,only_families=[]):
		# Load database
		databasePath = 'data/RMG_database'
		#if only_families: 
		#	print "Only loading reaction families %s"%only_families
		reaction.kineticsDatabase = ReactionFamilySet()
		reaction.kineticsDatabase.load(databasePath, only_families=only_families)

	
	def testEthaneExtrusionFromEther(self):
		"""A reaction that was giving trouble in a diesel simulation"""
		self.loadDatabase(only_families=['1,3_Insertion_ROR'])
		structure1 = Structure()
		structure1.fromSMILES("c1c([CH]C(C=CCCCCCC)OOCc2c3ccccc3ccc2)cccc1")
		species1, isNew = makeNewSpecies(structure1)
		
		structure2 = Structure()
		structure2.fromSMILES("c1ccc(c2ccccc12)COO")
		species2, isNew = makeNewSpecies(structure2)
		
		structure3 = Structure()
		structure3.fromSMILES("c1cc(C=C[C]=CCCCCCC)ccc1")
		species3, isNew = makeNewSpecies(structure3)
		
		# wipe the reaction list
		reaction.reactionDict = {}
		#print "FORWARD"
		rxns = reaction.kineticsDatabase.getReactions([species2,species3])
		#for rxn in rxns:
		#	print 'Reaction family:',rxn.family
		#	print 'Reaction:',rxn
		#	print 'Kinetics:',rxn.kinetics
		#	print 'bestKinetics:',rxn.bestKinetics
		#	print
		self.assertEqual(len(rxns),18, "Was expecting to make 18 reactions for %s + %s"%(species2,species3))
			
		# wipe the reaction list
		reaction.reactionDict = {}
		#print "REVERSE"
		rxns = reaction.kineticsDatabase.getReactions([species1])
		#for rxn in rxns:
		#	print 'Reaction family:',rxn.family
		#	print 'Reaction:',rxn
		#	print 'Kinetics:',rxn.kinetics
		#	print 'bestKinetics:',rxn.bestKinetics
		#	print
		self.assertEqual(len(rxns),1, "Was expecting to make 1 reaction for %s"%(species1))
		rxn = rxns[0]
		self.assertEqual(len(rxn.reactants),2,"Reaction wasn't bimolecular")
		self.assertTrue(species2 in rxn.reactants, "Didn't make %s"%species2)
		self.assertTrue(species3 in rxn.reactants, "Didn't make %s"%species3)

	def testIntraHmigration(self):
		"""An intra-H migration reaction"""
		self.loadDatabase(only_families=['intra_H_migration'])
		structure1 = Structure()
		structure1.fromSMILES("[CH](CCCc1ccccc1)CCCCCC")
		species1, isNew = makeNewSpecies(structure1)

		structure2 = Structure()
		structure2.fromSMILES("C(CCCC[CH]c1ccccc1)CCCC")
		species2, isNew = makeNewSpecies(structure2)
			
		# wipe the reaction list
		reaction.reactionDict = {}
		
		rxns = reaction.kineticsDatabase.getReactions([species1])
		#for rxn in rxns:
		#	print 'Reaction family:',rxn.family
		#	print 'Reaction:',rxn
		#	print 'Kinetics:',rxn.kinetics
		#	print 'bestKinetics:',rxn.bestKinetics
		#	print
		
		all_products = []
		for rxn in rxns:
			self.assertEqual(rxn.family.label,'Intra H migration',"Was trying to test 'Intra H migration' but made a reaction from family %s"%rxn.family)
			self.assertEqual(len(rxn.reactants),1,"Reaction %s wasn't unimolecular"%rxn)
			all_products.extend(rxn.products)
		self.assertTrue(species2 in all_products, "None of the reactions made %s"%(species2))

		#self.assertEqual(len(rxns),1, "Was expecting to make 1 reaction for %s"%(species1))

	def test12Cycloaddition(self):
		"""Test 1+2_Cycloaddition reactions"""
		self.loadDatabase(only_families=['1+2_Cycloaddition'])
		
		for smile in ['O1OO1'
					]:
			
			structure1 = Structure(SMILES=smile)
			species1, isNew = makeNewSpecies(structure1)
			print 'Reacting species',species1
				
			# wipe the reaction list
			reaction.reactionDict = {}
		
			rxns = reaction.kineticsDatabase.getReactions([species1])
			for rxn in rxns:
				print 'Reaction family:',rxn.family
				print 'Reaction:',rxn
				print 'Kinetics:',rxn.kinetics
				print
			
			all_products = []
			for rxn in rxns:
				#self.assertEqual(rxn.family.label,'Cyclic colligation',"Was trying to test 'Cyclic colligation' but made a reaction from family %s"%rxn.family)
				#self.assertEqual(len(rxn.reactants),1,"Reaction %s wasn't unimolecular"%rxn)
				#self.assertEqual(len(rxn.products),1,"Reaction %s wasn't unimolecular"%rxn)
				all_products.extend(rxn.products)
			print "All products for reacting %s:"%species1, [p.structure[0] for p in all_products]
			

		structure2 = Structure()
		structure2.fromAdjacencyList("O2\n1 O 0 {2,D}\n2 O 0 {1,D}\n")
		species2 = makeNewSpecies(structure2)
		structure3 = Structure()
		structure3.fromAdjacencyList("O\n1 O 2\n")
		species3 = makeNewSpecies(structure3)
		reaction.reactionDict = {}
		print "Now reacting %s with %s:"%(species2, species3)
		for sp in (species2, species3):
			print sp.toAdjacencyList()
		rxns = reaction.kineticsDatabase.getReactions([species2,species3])
		for rxn in rxns:
			print 'Reaction family:',rxn.family
			print 'Reaction:',rxn
			print 'Kinetics:',rxn.kinetics
		self.assertEqual(len(rxns),1, "Made %d 1+2_Cycloaddition reactions instead of 1"%(len(rxns)))
			
	def test22CycloadditionCd(self):
		"""Test 2+2_cycloaddition_Cd reactions"""
		self.loadDatabase(only_families=['2+2_cycloaddition_Cd'])
		
		for smile in [
				'C1(CC(C)(C)O1)(C)C'
					]:
			
			structure1 = Structure(SMILES=smile)
			species1, isNew = makeNewSpecies(structure1)
			print 'Reacting species',species1
				
			# wipe the reaction list
			reaction.reactionDict = {}
		
			rxns = reaction.kineticsDatabase.getReactions([species1])
			for rxn in rxns:
				print 'Reaction family:',rxn.family
				print 'Reaction:',rxn
				print 'Kinetics:',rxn.kinetics
				print
			
			all_products = []
			for rxn in rxns:
				#self.assertEqual(rxn.family.label,'Cyclic colligation',"Was trying to test 'Cyclic colligation' but made a reaction from family %s"%rxn.family)
				#self.assertEqual(len(rxn.reactants),1,"Reaction %s wasn't unimolecular"%rxn)
				#self.assertEqual(len(rxn.products),1,"Reaction %s wasn't unimolecular"%rxn)
				all_products.extend(rxn.products)
			print "All products for reacting %s:"%species1, [p.structure[0] for p in all_products]
			
								
			
	def testCyclicColligation(self):
		"""A test of a Birad_recombination  (Cyclic colligation) reactions"""
		self.loadDatabase(only_families=['Birad_recombination'])
		
		for smile in ['C1CCCCC1',
					  'CCCCCCCCC1C(c2ccccc2)C(CCCCCC)C=CC1c1ccccc1',
					  'C(=CC(c1ccccc1)C([CH]CCCCCC)C=Cc1ccccc1)[CH]CCCCCC',
					'C1(C(CCCCCCCC)C(C(CCCCCC)C=C1)c1ccccc1)c1ccccc1'
					]:
			
			structure1 = Structure(SMILES=smile)
			species1, isNew = makeNewSpecies(structure1)
			print 'Reacting species',species1
				
			# wipe the reaction list
			reaction.reactionDict = {}
		
			rxns = reaction.kineticsDatabase.getReactions([species1])
			for rxn in rxns:
				print 'Reaction family:',rxn.family
				print 'Reaction:',rxn
				print 'Kinetics:',rxn.kinetics
				print
				
			self.assertTrue(len(rxns)>0,"Didn't make any reactions!")
			
			all_products = []
			for rxn in rxns:
				self.assertEqual(rxn.family.label,'Cyclic colligation',"Was trying to test 'Cyclic colligation' but made a reaction from family %s"%rxn.family)
				self.assertEqual(len(rxn.reactants),1,"Reaction %s wasn't unimolecular"%rxn)
				self.assertEqual(len(rxn.products),1,"Reaction %s wasn't unimolecular"%rxn)
				all_products.extend(rxn.products)
				
			print "All products for reacting %s:"%species1, [p.structure[0] for p in all_products]
			
	def testDisproportionation(self):
		"""A test of a Disproportionation (Radical alpha H abstraction) reactions"""
		self.loadDatabase(only_families=['Disproportionation'])
		
		for smile in ['C(=[CH])[CH2]',
					]:
			
			structure1 = Structure(SMILES=smile)
			species1 = makeNewSpecies(structure1)
			print 'Reacting species',species1, 'with itself'
				
			# wipe the reaction list
			reaction.reactionDict = {}
		
			rxns = reaction.kineticsDatabase.getReactions([species1,species1])
			for rxn in rxns:
				print 'Reaction family:',rxn.family
				print 'Reaction:',rxn
				print 'Kinetics:',rxn.kinetics
				print
				
			self.assertTrue(len(rxns)>0,"Didn't make any reactions!")
			
			all_products = []
			for rxn in rxns:
				#self.assertEqual(rxn.family.label,'Cyclic colligation',"Was trying to test 'Cyclic colligation' but made a reaction from family %s"%rxn.family)
				self.assertEqual(len(rxn.reactants),2,"Reaction %s wasn't bimolecular"%rxn)
				self.assertEqual(len(rxn.products),2,"Reaction %s wasn't bimolecular"%rxn)
				all_products.extend(rxn.products)
				
			print "All products for reacting %s:"%species1, [p.structure[0] for p in all_products]
			
	
	def testAllFamilies(self):
		"""A test of all reaction families
		
		Doesn't do (m)any actual tests, but hopefully won't cause any errors"""
		self.loadDatabase()
		
		for smile in ['O1OO1',
					'C1(CC(C)(C)O1)(C)C',
					'C1(C(CCCCCCCC)C(C(CCCCCC)C=C1)c1ccccc1)c1ccccc1',
					'C(C)(C)(C)C(=O)OCC(C)C']:
			structure1 = Structure(SMILES=smile)
			species1, isNew = makeNewSpecies(structure1)
			print 'Reacting species',species1
				
			# wipe the reaction list
			reaction.reactionDict = {}
		
			rxns = reaction.kineticsDatabase.getReactions([species1])
			
			all_products = []
			for rxn in rxns:
				all_products.extend(rxn.products)
				
			print "All products for reacting %s:"%species1, [p.structure[0] for p in all_products]
			
			


################################################################################
from timeit import Timer
if __name__ == '__main__':
	
	
	startup = """gc.enable() # enable garbage collection in timeit
import sys
sys.path.append('../source')
from rmg.structure import Structure
from rmg.species import makeNewSpecies
from rmg.reaction import makeNewReaction
structure1 = Structure()
structure1.fromAdjacencyList('''
1 C 0 {2,D} {7,S} {8,S}
2 C 0 {1,D} {3,S} {9,S}
3 C 0 {2,S} {4,D} {10,S}
4 C 0 {3,D} {5,S} {11,S}
5 *1 C 0 {4,S} {6,S} {12,S} {13,S}
6 C 0 {5,S} {14,S} {15,S} {16,S}
7 H 0 {1,S}
8 H 0 {1,S}
9 H 0 {2,S}
10 H 0 {3,S}
11 H 0 {4,S}
12 *2 H 0 {5,S}
13 H 0 {5,S}
14 H 0 {6,S}
15 H 0 {6,S}
16 H 0 {6,S}
''')

structure2 = Structure()
structure2.fromAdjacencyList('''
1 *3 H 1
''')

structure3 = Structure()
structure3.fromAdjacencyList('''
1 C 0 {2,D} {7,S} {8,S}
2 C 0 {1,D} {3,S} {9,S}
3 C 0 {2,S} {4,D} {10,S}
4 C 0 {3,D} {5,S} {11,S}
5 *3 C 1 {4,S} {6,S} {12,S}
6 C 0 {5,S} {13,S} {14,S} {15,S}
7 H 0 {1,S}
8 H 0 {1,S}
9 H 0 {2,S}
10 H 0 {3,S}
11 H 0 {4,S}
12 H 0 {5,S}
13 H 0 {6,S}
14 H 0 {6,S}
15 H 0 {6,S}
''')

structure4 = Structure()
structure4.fromAdjacencyList('''
1 *1 H 0 {2,S}
2 *2 H 0 {1,S}
''')

C6H10, isNew = makeNewSpecies(structure1)
H, isNew = makeNewSpecies(structure2)
C6H9, isNew = makeNewSpecies(structure3)
H2, isNew = makeNewSpecies(structure4)

reaction1, isNew = makeNewReaction([C6H9, H2], [C6H10, H], \
	[C6H9.structure[0], H2.structure[0]], \
	[C6H10.structure[0], H.structure[0]], \
	None)
"""
	test1 = "reaction1, isNew = makeNewReaction([C6H9, H2], [C6H10, H], [C6H9.structure[0], H2.structure[0]], [C6H10.structure[0], H.structure[0]], None)"
	print "Timing makeNewReaction:"
	t = Timer(test1,startup)
#	times = t.repeat(repeat=1,number=10000)
#	print " Test1 took %.3f microseconds (%s)"%(min(times)*1000/10, [tt*1000/10 for tt in times])
	print "**************"
	
	# run a certain check without catching errors (turn on PDB debugger first)
	import rmg.log as logging
	logging.initialize(5,'reactiontest.log') 
	#import pdb
	ReactionSetCheck('test12Cycloaddition').debug()
	
	# now run all the unit tests
	unittest.main( testRunner = unittest.TextTestRunner(verbosity=2) )
