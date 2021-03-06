#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script generates a video showing the flux diagram for a given reaction
model as it evolves in time. It takes as its lone required argument the path
to an RMG-Py input file corresponding to a job that has already been run.
This script will automatically read from the necessary output files to extract
the information needed to generate the flux diagram.
"""

import os.path
import re
import math
import numpy
import pydot

from rmgpy.chemkin import loadChemkinFile
from rmgpy.rmg.main import RMG
from rmgpy.solver.base import TerminationTime, TerminationConversion
from rmgpy.solver.simple import SimpleReactor

################################################################################

# Here you can set the default values for options that control the generated
# flux diagrams.

# Options controlling the individual flux diagram renderings:
program = 'dot'                 # The program to use to lay out the nodes and edges
maximumNodeCount = 50           # The maximum number of nodes to show in the diagram
maximumEdgeCount = 50           # The maximum number of edges to show in the diagram
concentrationTolerance = 1e-6   # The lowest fractional concentration to show (values below this will appear as zero)
speciesRateTolerance = 1e-6     # The lowest fractional species rate to show (values below this will appear as zero)
maximumNodePenWidth = 10.0      # The thickness of the border around a node at maximum concentration
maximumEdgePenWidth = 10.0      # The thickness of the edge at maximum species rate

# Options controlling the ODE simulations:
initialTime = 1e-12             # The time at which to initiate the simulation, in seconds
timeStep = 10**0.1              # The multiplicative factor to use between consecutive time points
absoluteTolerance = 1e-16       # The absolute tolerance to use in the ODE simluations
relativeTolerance = 1e-8        # The relative tolerance to use in the ODE simulations

# Options controlling the generated movie:
framesPerSecond = 6             # The number of frames per second in the generated movie
initialPadding = 5              # The number of seconds to display the initial fluxes at the start of the video
finalPadding = 5                # The number of seconds to display the final fluxes at the end of the video

################################################################################

def generateFluxDiagram(reactionModel, times, concentrations, reactionRates, outputDirectory, centralSpecies=None, speciesDirectory=None, settings=None):
    """
    For a given `reactionModel` and simulation results stored as arrays of
    `times`, species `concentrations`, and `reactionRates`, generate a series
    of flux diagrams as frames of an animation, then stitch them together into
    a movie. The individual frames and the final movie are saved on disk at
    `outputDirectory.`
    """
    global maximumNodeCount, maximumEdgeCount, timeStep, concentrationTolerance, speciesRateTolerance
    # Allow user defined settings for flux diagram generation if given
    if settings:
        maximumNodeCount = settings['maximumNodeCount']       
        maximumEdgeCount = settings['maximumEdgeCount']  
        timeStep = settings['timeStep']
        concentrationTolerance = settings['concentrationTolerance']   
        speciesRateTolerance = settings['speciesRateTolerance']
    
    # Get the species and reactions corresponding to the provided concentrations and reaction rates
    speciesList = reactionModel.core.species[:]
    numSpecies = len(speciesList)
    reactionList = reactionModel.core.reactions[:]
    numReactions = len(reactionList)
    
    #search index of central species:
    if centralSpecies is not None:
        for i, species in enumerate(speciesList):
            if species.label == centralSpecies:
                centralSpeciesIndex = i
                break 
    
    # Compute the rates between each pair of species (big matrix warning!)
    speciesRates = numpy.zeros((len(times),numSpecies,numSpecies), numpy.float64)
    for index, reaction in enumerate(reactionList):
        rate = reactionRates[:,index]
        if not reaction.pairs: reaction.generatePairs()
        for reactant, product in reaction.pairs:
            reactantIndex = speciesList.index(reactant)
            productIndex = speciesList.index(product)
            speciesRates[:,reactantIndex,productIndex] += rate
            speciesRates[:,productIndex,reactantIndex] -= rate
    
    # Determine the maximum concentration for each species and the maximum overall concentration
    maxConcentrations = numpy.max(numpy.abs(concentrations), axis=0)
    maxConcentration = numpy.max(maxConcentrations)
    
    # Determine the maximum rate for each species-species pair and the maximum overall species-species rate
    maxSpeciesRates = numpy.max(numpy.abs(speciesRates), axis=0)
    maxSpeciesRate = numpy.max(maxSpeciesRates)
    speciesIndex = maxSpeciesRates.reshape((numSpecies*numSpecies)).argsort()
    
    # Determine the nodes and edges to keep
    nodes = []; edges = []
    if centralSpecies is None:
        for i in range(numSpecies*numSpecies):
            productIndex, reactantIndex = divmod(speciesIndex[-i-1], numSpecies)
            if reactantIndex > productIndex:
                # Both reactant -> product and product -> reactant are in this list,
                # so only keep one of them
                continue
            if maxSpeciesRates[reactantIndex, productIndex] == 0:
                break
            if reactantIndex not in nodes and len(nodes) < maximumNodeCount: nodes.append(reactantIndex)
            if productIndex not in nodes and len(nodes) < maximumNodeCount: nodes.append(productIndex)
            if len(nodes) > maximumNodeCount: 
                break
            edges.append([reactantIndex, productIndex])
            if len(edges) >= maximumEdgeCount:
                break
    else:
        nodes.append(centralSpeciesIndex)
        for index, reaction in enumerate(reactionList):
            for reactant, product in reaction.pairs:
                reactantIndex = speciesList.index(reactant)
                productIndex = speciesList.index(product)
                if maxSpeciesRates[reactantIndex, productIndex] == 0:
                    break
                if len(nodes) > maximumNodeCount or len(edges) >= maximumEdgeCount: 
                    break
                if reactantIndex == centralSpeciesIndex: 
                    if productIndex not in nodes:
                        nodes.append(productIndex)
                        edges.append([reactantIndex, productIndex])
                if productIndex == centralSpeciesIndex: 
                    if reactantIndex not in nodes:
                        nodes.append(reactantIndex)
                        edges.append([reactantIndex, productIndex])
    # Create the master graph
    # First we're going to generate the coordinates for all of the nodes; for
    # this we use the thickest pen widths for all nodes and edges 
    graph = pydot.Dot('flux_diagram', graph_type='digraph', overlap="false")
    graph.set_rankdir('LR')
    graph.set_fontname('sans')
    graph.set_fontsize('10')
    # Add a node for each species
    for index in nodes:
        species = speciesList[index]
        node = pydot.Node(name=species.label)
        node.set_penwidth(maximumNodePenWidth)
        graph.add_node(node)
        # Try to use an image instead of the label
        speciesIndex = re.search('\(\d+\)$', species.label).group(0) + '.png'
        imagePath = ''
        if not speciesDirectory or not os.path.exists(speciesDirectory): 
            continue
        for root, dirs, files in os.walk(speciesDirectory):
            for f in files:
                if f.endswith(speciesIndex):
                    imagePath = os.path.join(root, f)
                    break
        if os.path.exists(imagePath):
            node.set_image(imagePath)
            node.set_label(" ")
    # Add an edge for each species-species rate
    for reactantIndex, productIndex in edges:
        if reactantIndex in nodes and productIndex in nodes:
            reactant = speciesList[reactantIndex]
            product = speciesList[productIndex]
            edge = pydot.Edge(reactant.label, product.label)
            edge.set_penwidth(maximumEdgePenWidth)
            graph.add_edge(edge) 
    
    # Generate the coordinates for all of the nodes using the specified program
    graph = pydot.graph_from_dot_data(graph.create_dot(prog=program))
    
    # Now iterate over the time points, setting the pen widths appropriately
    # This should preserve the coordinates of the nodes from frame to frame
    frameNumber = 1
    for t in range(len(times)):
        # Update the nodes
        slope = -maximumNodePenWidth / math.log10(concentrationTolerance)
        for index in nodes:
            species = speciesList[index]
            node = graph.get_node('"{0}"'.format(species.label))[0]
            concentration = concentrations[t,index] / maxConcentration
            if concentration < concentrationTolerance:
                penwidth = 0.0
            else:
                penwidth = slope * math.log10(concentration) + maximumNodePenWidth
            node.set_penwidth(penwidth)
        # Update the edges
        slope = -maximumEdgePenWidth / math.log10(speciesRateTolerance)
        for index in range(len(edges)):
            reactantIndex, productIndex = edges[index]
            if reactantIndex in nodes and productIndex in nodes:
                reactant = speciesList[reactantIndex]
                product = speciesList[productIndex]
                edge = graph.get_edge('"{0}"'.format(reactant.label), '"{0}"'.format(product.label))[0]
                # Determine direction of arrow based on sign of rate
                speciesRate = speciesRates[t,reactantIndex,productIndex] / maxSpeciesRate
                if speciesRate < 0:
                    edge.set_dir("back")
                    speciesRate = -speciesRate
                else:
                    edge.set_dir("forward")
                # Set the edge pen width
                if speciesRate < speciesRateTolerance:
                    penwidth = 0.0
                    edge.set_dir("none")
                else:
                    penwidth = slope * math.log10(speciesRate) + maximumEdgePenWidth
                edge.set_penwidth(penwidth)
        # Save the graph at this time to a dot file and a PNG image
        if times[t] == 0:
            label = 't = 0 s'
        else:
            label = 't = 10^{0:.1f} s'.format(math.log10(times[t]))
        graph.set_label(label)
        if t == 0:
            repeat = framesPerSecond * initialPadding
        elif t == len(times) - 1:
            repeat = framesPerSecond * finalPadding
        else:
            repeat = 1
        for r in range(repeat):
            graph.write_dot(os.path.join(outputDirectory, 'flux_diagram_{0:04d}.dot'.format(frameNumber)))
            graph.write_png(os.path.join(outputDirectory, 'flux_diagram_{0:04d}.png'.format(frameNumber)))
            frameNumber += 1
    
    # Use mencoder to stitch the PNG images together into a movie
    import subprocess
    command = ('mencoder',
        'mf://*.png',
        '-mf',
        'type=png:fps={0:d}'.format(framesPerSecond),
        '-ovc',
        'lavc',
        '-lavcopts',
        'vcodec=mpeg4',
        '-oac',
        'copy',
        '-o',
        'flux_diagram.avi',
    )
    subprocess.check_call(command, cwd=outputDirectory)
    
################################################################################

def simulate(reactionModel, reactionSystem, settings = None):
    """
    Generate and return a set of core and edge species and reaction fluxes
    by simulating the given `reactionSystem` using the given `reactionModel`.
    """
    global maximumNodeCount, maximumEdgeCount, timeStep, concentrationTolerance, speciesRateTolerance
    # Allow user defined settings for flux diagram generation if given
    if settings:
        maximumNodeCount = settings['maximumNodeCount']       
        maximumEdgeCount = settings['maximumEdgeCount']  
        timeStep = settings['timeStep']
        concentrationTolerance = settings['concentrationTolerance']   
        speciesRateTolerance = settings['speciesRateTolerance']
    
    coreSpecies = reactionModel.core.species
    coreReactions = reactionModel.core.reactions
    edgeSpecies = reactionModel.edge.species
    edgeReactions = reactionModel.edge.reactions
    
#    numCoreSpecies = len(coreSpecies)
#    numCoreReactions = len(coreReactions)
#    numEdgeSpecies = len(edgeSpecies)
#    numEdgeReactions = len(edgeReactions)
    
    speciesIndex = {}
    for index, spec in enumerate(coreSpecies):
        speciesIndex[spec] = index
    
    reactionSystem.initializeModel(coreSpecies, coreReactions, edgeSpecies, edgeReactions, [], absoluteTolerance, relativeTolerance)

    # Copy the initial conditions to use in evaluating conversions
    y0 = reactionSystem.y.copy()

    time = []
    coreSpeciesConcentrations = []
    coreReactionRates = []
    edgeReactionRates = []

    nextTime = initialTime
    terminated = False; iteration = 0
    while not terminated:
        # Integrate forward in time to the next time point
        reactionSystem.advance(nextTime)

        iteration += 1
        
        time.append(reactionSystem.t)
        coreSpeciesConcentrations.append(reactionSystem.coreSpeciesConcentrations)
        coreReactionRates.append(reactionSystem.coreReactionRates)
        edgeReactionRates.append(reactionSystem.edgeReactionRates)
        
        # Finish simulation if any of the termination criteria are satisfied
        for term in reactionSystem.termination:
            if isinstance(term, TerminationTime):
                if reactionSystem.t > term.time.value:
                    terminated = True
                    break
            elif isinstance(term, TerminationConversion):
                index = speciesIndex[term.species]
                if (y0[index] - reactionSystem.y[index]) / y0[index] > term.conversion:
                    terminated = True
                    break

        # Increment destination step time if necessary
        if reactionSystem.t >= 0.9999 * nextTime:
            nextTime *= timeStep

    time = numpy.array(time)
    coreSpeciesConcentrations = numpy.array(coreSpeciesConcentrations)
    coreReactionRates = numpy.array(coreReactionRates)
    edgeReactionRates = numpy.array(edgeReactionRates)
    
    return time, coreSpeciesConcentrations, coreReactionRates, edgeReactionRates

################################################################################

def loadChemkinOutput(outputFile, reactionModel):
    """
    Load the species concentrations from a Chemkin Output file in a simulation
    and generate the reaction rates at each time point.
    """
    from rmgpy.quantity import Quantity, constants

    coreReactions = reactionModel.core.reactions
    edgeReactions = reactionModel.edge.reactions    
    speciesList = reactionModel.core.species

    time = []
    coreSpeciesConcentrations = []
    coreReactionRates = []
    edgeReactionRates = []

    with open(outputFile, 'r') as f:

        line = f.readline()
        while line != '' and 'SPECIFIED END' not in line:
            line.strip()
            tokens = line.split()
            if ' TIME ' in line:
                # Time is in seconds
                time.append(float(tokens[-2]))
            elif ' PRESSURE ' in line:
                # Pressure from Chemkin is in atm    
                P = Quantity(float(tokens[-2]),'atm')
            elif ' TEMPERATURE ' in line:
                # Temperature from Chemkin in in K
                T = Quantity(float(tokens[-2]),'K')
            elif ' MOLE FRACTIONS ' in line:
                # Species always come in the same order as listed in chem.inp
                molefractions = []
                line = f.readline() # This one reads the blank line which follows
                line = f.readline()
                while line.strip() != '':
                    tokens = line.split()
                    for value in tokens[2::3]:      
                        
                        # Make all concentrations positive 
                        if value.find('-') == 0:
                                value = value.replace('-','',1) 
                        # Sometimes chemkin removes the `E` in scientific notation due to lack of space, 
                        # rendering invalid float values.  If this is the case, add it in.      
                        if value.find('-') != -1:
                            if value.find('E') == -1:
                                value = value.replace('-','E-')
                                                 
                        molefractions.append(float(value))       
           
                    line = f.readline()

                totalConcentration = P.value/constants.R/T.value
                coreSpeciesConcentrations.append([molefrac*totalConcentration for molefrac in molefractions])
                coreRates = []
                edgeRates = []
                for reaction in coreReactions:                    
                    rate = reaction.getRateCoefficient(T.value,P.value)
                    for reactant in reaction.reactants:
                        rate *= molefractions[speciesList.index(reactant)]*totalConcentration                    
                    coreRates.append(rate)
                for reaction in edgeReactions:
                    edgeRates.append(reaction.getRateCoefficient(T.value,P.value))

                if coreRates:
                    coreReactionRates.append(coreRates)
                if edgeRates:
                    edgeReactionRates.append(edgeRates)
            
            line=f.readline()
   
    time = numpy.array(time)
    coreSpeciesConcentrations = numpy.array(coreSpeciesConcentrations)
    coreReactionRates = numpy.array(coreReactionRates)
    edgeReactionRates = numpy.array(edgeReactionRates)
   
    return time, coreSpeciesConcentrations, coreReactionRates, edgeReactionRates

################################################################################

def loadRMGJavaJob(inputFile, chemkinFile=None, speciesDict=None):
    """
    Load the results of an RMG-Java job generated from the given `inputFile`.
    """
    
    from rmgpy.molecule import Molecule
    
    # Load the specified RMG-Java input file
    # This implementation only gets the information needed to generate flux diagrams
    rmg = RMG()
    rmg.loadRMGJavaInput(inputFile)
    rmg.outputDirectory = os.path.abspath(os.path.dirname(inputFile))
    
    # Load the final Chemkin model generated by RMG-Java
    if not chemkinFile:
        chemkinFile = os.path.join(os.path.dirname(inputFile), 'chemkin', 'chem.inp')
    if not speciesDict:
        speciesDict = os.path.join(os.path.dirname(inputFile), 'RMG_Dictionary.txt')
    speciesList, reactionList = loadChemkinFile(chemkinFile, speciesDict)
    
    # Bath gas species don't appear in RMG-Java species dictionary, so handle
    # those as a special case
    for species in speciesList:
        if species.label == 'Ar':
            species.molecule = [Molecule().fromSMILES('[Ar]')]
        elif species.label == 'Ne':
            species.molecule = [Molecule().fromSMILES('[Ne]')]
        elif species.label == 'He':
            species.molecule = [Molecule().fromSMILES('[He]')]
        elif species.label == 'N2':
            species.molecule = [Molecule().fromSMILES('N#N')]
    
    # Map species in input file to corresponding species in Chemkin file
    speciesDict = {}
    for spec0 in rmg.initialSpecies:
        for species in speciesList:
            if species.isIsomorphic(spec0):
                speciesDict[spec0] = species
                break
            
    # Generate flux pairs for each reaction if needed
    for reaction in reactionList:
        if not reaction.pairs: reaction.generatePairs()

    # Replace species in input file with those in Chemkin file
    for reactionSystem in rmg.reactionSystems:
        reactionSystem.initialMoleFractions = dict([(speciesDict[spec], frac) for spec, frac in reactionSystem.initialMoleFractions.iteritems()])
        for t in reactionSystem.termination:
            if isinstance(t, TerminationConversion):
                if t.species not in speciesDict.values():
                    t.species = speciesDict[t.species]
    
    # Set reaction model to match model loaded from Chemkin file
    rmg.reactionModel.core.species = speciesList
    rmg.reactionModel.core.reactions = reactionList
    
    # RMG-Java doesn't generate species images, so draw them ourselves now
    speciesPath = os.path.join(os.path.dirname(inputFile), 'species')
    try:
        os.mkdir(speciesPath)
    except OSError:
        pass
    for species in speciesList:

        path = os.path.join(speciesPath + '/{0!s}.png'.format(species))
        species.molecule[0].draw(str(path))
    
    return rmg

################################################################################

def loadRMGPyJob(inputFile, chemkinFile=None, speciesDict=None):
    """
    Load the results of an RMG-Py job generated from the given `inputFile`.
    """
    
    # Load the specified RMG input file
    rmg = RMG()
    rmg.loadInput(inputFile)
    rmg.outputDirectory = os.path.abspath(os.path.dirname(inputFile))
    
    # Load the final Chemkin model generated by RMG
    if not chemkinFile:
        chemkinFile = os.path.join(os.path.dirname(inputFile), 'chemkin', 'chem.inp')
    if not speciesDict:
        speciesDict = os.path.join(os.path.dirname(inputFile), 'chemkin', 'species_dictionary.txt')
    speciesList, reactionList = loadChemkinFile(chemkinFile, speciesDict)
    
    # Map species in input file to corresponding species in Chemkin file
    speciesDict = {}
    for spec0 in rmg.initialSpecies:
        for species in speciesList:
            if species.isIsomorphic(spec0):
                speciesDict[spec0] = species
                break
            
    # Generate flux pairs for each reaction if needed
    for reaction in reactionList:
        if not reaction.pairs: reaction.generatePairs()
    
    # Replace species in input file with those in Chemkin file
    for reactionSystem in rmg.reactionSystems:
        reactionSystem.initialMoleFractions = dict([(speciesDict[spec], frac) for spec, frac in reactionSystem.initialMoleFractions.iteritems()])
        for t in reactionSystem.termination:
            if isinstance(t, TerminationConversion):
                t.species = speciesDict[t.species]
    
    # Set reaction model to match model loaded from Chemkin file
    rmg.reactionModel.core.species = speciesList
    rmg.reactionModel.core.reactions = reactionList

    # Generate species images
    speciesPath = os.path.join(os.path.dirname(inputFile), 'species')
    try:
        os.mkdir(speciesPath)
    except OSError:
        pass
    for species in speciesList:
        path = os.path.join(speciesPath, '{0!s}.png'.format(species))
        if not os.path.exists(path):
            species.molecule[0].draw(str(path))
    
    return rmg

################################################################################

def createFluxDiagram(savePath, inputFile, chemkinFile, speciesDict, java = False, settings = None, chemkinOutput = '', centralSpecies = None):
    """
    Generates the flux diagram based on a condition 'inputFile', chemkin.inp chemkinFile,
    a speciesDict txt file, plus an optional chemkinOutput file.
    """
    if java:
        rmg = loadRMGJavaJob(inputFile, chemkinFile, speciesDict)
    else:
        rmg = loadRMGPyJob(inputFile, chemkinFile, speciesDict)

    speciesPath = os.path.join(os.path.dirname(inputFile), 'species')
    
    # if you have a chemkin output, then you only have one reactionSystem
    if chemkinOutput:
        try:
            os.makedirs(os.path.join(savePath,'1'))
        except OSError:
            pass

        print 'Extracting species concentrations and calculating reaction rates from chemkin output...'
        time, coreSpeciesConcentrations, coreReactionRates, edgeReactionRates = loadChemkinOutput(chemkinOutput, rmg.reactionModel)

        print 'Generating flux diagram for chemkin output...'
        generateFluxDiagram(rmg.reactionModel, time, coreSpeciesConcentrations, coreReactionRates, os.path.join(savePath, '1'), centralSpecies, speciesPath, settings)

    else:
        # Generate a flux diagram video for each reaction system
        for index, reactionSystem in enumerate(rmg.reactionSystems):
            try:
                os.makedirs(os.path.join(savePath,'{0:d}'.format(index+1)))
            except OSError:
            # Fail silently on any OS errors
                pass

            #rmg.makeOutputSubdirectory('flux/{0:d}'.format(index+1))

            # If there is no termination time, then add one to prevent jobs from
            # running forever
            if not any([isinstance(term, TerminationTime) for term in reactionSystem.termination]):
                reactionSystem.termination.append(TerminationTime((1e10,'s')))

            print 'Conducting simulation of reaction system {0:d}...'.format(index+1)
            time, coreSpeciesConcentrations, coreReactionRates, edgeReactionRates = simulate(rmg.reactionModel, reactionSystem, settings)

            print 'Generating flux diagram for reaction system {0:d}...'.format(index+1)
            generateFluxDiagram(rmg.reactionModel, time, coreSpeciesConcentrations, coreReactionRates, os.path.join(savePath, '{0:d}'.format(index+1)), 
                                centralSpecies, speciesPath, settings)
################################################################################

if __name__ == '__main__':
    # This might not work anymore because functions were modified for use with webserver

    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('input', metavar='INPUT', type=str, nargs=1,
        help='the RMG input file to use')
    parser.add_argument('--java', action='store_true', help='process RMG-Java model')
    args = parser.parse_args()
    inputFile = os.path.abspath(args.input[0])
    
    if args.java:
        # The argument is an RMG-Java input file
        rmg = loadRMGJavaJob(inputFile)
        
    else:
        # The argument is an RMG-Py input file
        rmg = loadRMGPyJob(inputFile)
        
    # Generate a flux diagram video for each reaction system
    rmg.makeOutputSubdirectory('flux')
    for index, reactionSystem in enumerate(rmg.reactionSystems):
        
        rmg.makeOutputSubdirectory('flux/{0:d}'.format(index+1))
        
        # If there is no termination time, then add one to prevent jobs from
        # running forever
        if not any([isinstance(term, TerminationTime) for term in reactionSystem.termination]):
            reactionSystem.termination.append(TerminationTime((1e10,'s')))
        
        speciesPath = os.path.join(os.path.dirname(inputFile), 'species')
        
        print 'Conducting simulation of reaction system {0:d}...'.format(index+1)
        time, coreSpeciesConcentrations, coreReactionRates, edgeReactionRates = simulate(rmg.reactionModel, reactionSystem)
        
        centralSpecies = None
        print 'Generating flux diagram for reaction system {0:d}...'.format(index+1)
        generateFluxDiagram(rmg.reactionModel, time, coreSpeciesConcentrations, coreReactionRates, os.path.join(rmg.outputDirectory, 'flux', '{0:d}'.format(index+1)), centralSpecies, speciesPath)
