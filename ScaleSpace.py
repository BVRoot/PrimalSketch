from __future__ import division		# allows '//' to mean integer division
import numpy
import Watershed as ws
#import scipy.special		# for the .kn() "modified Bessel function"
import scipy.signal		# for sepfir2d() and gaussian()


class ScaleSpace_Blob :
	def __init__(self, idNum) :
		self.isBright = None
		self.signifVal = None
		self.appearance = None
		self.disappearance = None
		self.idNum = idNum

		# This will list the grey blob for scale each level.
		self.grey_blobs = []
		# This will list the support region for each scale level
		self.support_regions = []
		# This will list the Scale_Level for each scale level
		self.scale_levels = []
		# This will list the scale event for each scale level
		self.events = []

		self.approp_scalelvl = None
		self.approp_greyblob = None
		self.atBoundary = None


	def Start_ScaleBlob(self, greyBlob, scaleLevel) :
		greyBlob.scaleBlob = self

		self.appearance = scaleLevel
		self.disappearance = scaleLevel
		self.grey_blobs.append(greyBlob)
		self.support_regions.append(greyBlob.support_region)
		self.scale_levels.append(scaleLevel)

		newEvent = Scale_Event(Scale_Event.CREATION,
                                       [], [self],
                                       greyBlob.support_region.first_moment(),
                                       scaleLevel)
		self.events.append(newEvent)
		return newEvent

	def End_ScaleBlob(self) :
		endEvent = Scale_Event(Scale_Event.DESTRUCTION,
				       [self], [],
				       self.support_regions[-1].first_moment(),
				       self.scale_levels[-1])
		self.events.append(endEvent)
		return endEvent

	def Continue_ScaleBlob(self, greyBlob, scaleLevel) :
		greyBlob.scaleBlob = self
		self.disappearance = scaleLevel
		self.support_regions.append(greyBlob.support_region)
		self.grey_blobs.append(greyBlob)
		self.scale_levels.append(scaleLevel)

#	def Split_ScaleBlob(self, greyBlob) :
#		# So, we split a scale blob by updating the last event in the events list
#		# Note that this function assumes that in order to know that a split has
#		#      occurred, that the scale blob has already been "continued", and that
#		#      the splits are being discovered one grey blob at a time.
#		self.support_regions[-1].AddSupport(greyBlob.support_region)
#		self.grey_blobs[-1].append(greyBlob)
#		
#		self.events[-1][-1].event_type = Scale_Event.SPLIT
#		self.events[-1][-1].position = self.support_regions[-1].first_moment()
#
#		return self.events[-1][-1]

#	def Merge_ScaleBlob(self, greyBlob, scaleBlobs, scaleLevel) :
#
#		self.events[-1][-1].event_type = Scale_Event.MERGE
#		self.events[-1][-1].scaleblobs_above += scaleBlobs
#		# TODO: Hmm, need to also update position, but how?
#
#		return self.events[-1][-1]
		

#	def Add_Greylevel_Blobs(self, blobs, scale_lev) :
#		new_support = ws.Support_Region()
#
#		for aBlob in blobs :
#			aBlob.scalespace_blob = self
#			new_support.AddSupport(aBlob.support_region)
#
#		self.support_regions.append(new_support)
#		self.grey_blobs.append(blobs)
#		self.scale_levels.append(scale_lev)
#
#	def Add_Greylevel_Blob(self, aBlob) :
#		# Assumes that we are adding one blob to the current level.
#		# Therefore, a level must exist first...
#		aBlob.scalespace_blob = self
#		self.support_regions[-1].AddSupport(aBlob.support_region)
#		self.grey_blobs[-1].append(aBlob)




class Scale_Event :
	CREATION = 0
	SPLIT = 1
	MERGE = 2
	DESTRUCTION = 3

	def __init__(self, event_type, scaleblobs_above = [], scaleblobs_below = [], position = None, scale_lev = None) :
		self.event_type = event_type
		self.scaleblobs_above = scaleblobs_above
		self.scaleblobs_below = scaleblobs_below
		self.position = position
		self.scale_level = scale_lev



UNMARKED = -1

class Scale_Level :
	def __init__(self, greyBlobs, image, greyMarks, scaleVal) :
		self.scaleVal = scaleVal
		self.image = image

		if greyMarks is None :
			self.greyMarks = numpy.empty(image.shape, dtype=int)
			self.greyMarks.fill(UNMARKED)
		else :
			self.greyMarks = greyMarks

		self.greyBlobs = greyBlobs
		self.scaleMarks = numpy.empty(image.shape, dtype=int)
		self.scaleMarks.fill(UNMARKED)



def Mark_ScaleBlob(aGreyBlob, scaleBlob_Label, idNum) :
	for anIndex in aGreyBlob.support_region :
		scaleBlob_Label[anIndex] = idNum



class Primal_Sketch :
	def __init__(self) :
		self.scale_levels = {}

		self.scaleBlobs_bright = []
		self.events_bright = []

		self.currIDNum = 0


	def CreateSketch(self, image, scale_values, refinementLimit = 5) :
		if len(scale_values) == 0 :
			print "No scales given!"
			return

		# Makes sure that the values are sorted from greatest to least.
		scale_values.sort()
		scale_values.reverse()


		# Dummy scale level for priming the pump purposes.
		prevScale = Scale_Level([], image, None, scale_values[-1])

		refinementCnt = 0
		isForced = False		# Used to force linkage and prevent scale refinement in certain situations.
		

		# NOTE: scale_values may get dynamically updated within the loop as refinement occurs.
		while len(scale_values) > 0 :
			aScale = scale_values.pop()
			print "Working level:", aScale

			# This if statement allows for use of caching during the scale refinement process.
			if aScale not in self.scale_levels :
				if aScale == 0 :
					newImage = image.copy()
				else :
					newImage = self.DoConvolve(image, aScale, (4 * (aScale // 2)) + 3).astype(int)

				print "At level: ", aScale #, "  Image max:", newImage.max(), "   Image min:", newImage.min()
			
				greyblobs, greyMarks = ws.Watershed_Transform(newImage)
				newScale = Scale_Level(greyblobs, image, greyMarks, aScale)
				self.scale_levels[aScale] = newScale
			else :
				newScale = self.scale_levels[aScale]


			isAmbiguous, candidates = self.Find_Candidates(prevScale, newScale)

			if not isAmbiguous or isForced :
				print "Is it Ambiguous?", isAmbiguous
				self.Link_GreyBlobs(candidates, newScale)
				prevScale = newScale
				refinementCnt = 0
				isForced = False
			else :
				print "Refining..."
				refinementCnt += 1
				# Ah, an ambiguity! Therefore, we need to put the current scale level off and
				#   dynamically try for some intermediate scale level, if possible.
				scale_values.append(aScale)

				refineScale = int(self.ScaleTrans_Inverse((self.ScaleTrans(aScale) + 
									   self.ScaleTrans(prevScale.scaleVal)) / 2.0))

				if (refinementCnt >= refinementLimit) or (refineScale in self.scale_levels) or (refineScale in scale_values) :
					# Either we have done too much refinement or the integer limitation
					# caused us to calculate an already existing scale level.
					# Therefore, we shall force the linkage of the current candidates.
					isForced = True
				else :
					# place the new scale value at the top of the stack.
					scale_values.append(refineScale)
					isForced = False

		# End while len(scale_values) > 0




	def DoConvolve(self, image, scale_level, winSize) :
		# NOTE: I know this isn't technically the best approach.
		# There is supposedly a better way using Bessel functions,
		#  but until I get a better idea how this is supposed to be
		#  implemented, I will do it this way.
		kernel = scipy.signal.gaussian(winSize, scale_level)
		return scipy.signal.sepfir2d(image, kernel / kernel.sum(),
						    kernel / kernel.sum())

#	def AddNewScaleLevel(self, image, greyblobs, greyMarks, scaleVal) :
#		# Right now, assume that the scale size is changing monotonically.
#		# Therefore, I won't bother with trying to sort and mess around with linkage issues.
#		self.scale_levels.append(Scale_Level(greyblobs, image, greyMarks, scaleVal))

	def ScaleTrans(self, scaleVal) :
		# Just a stub until I truely implement this
		return scaleVal

	def ScaleTrans_Inverse(self, scaleVal) :
		# Just a stub until I truely implement this
		return scaleVal

		
	def Find_Candidates(self, prevScale, currScale) :
		ignoreThese = frozenset([UNMARKED])
		

		currScale_candidates = {}
		for aGreyBlob in currScale.greyBlobs :
			# Find out which grey blobs existed at the previous scale level at the location
			# of this grey blob's extremum. We automatically removed any UNMARKED as well.
			greyIndices = set([prevScale.greyMarks[anIndex] for anIndex in aGreyBlob.extremum]) - ignoreThese

			currScale_candidates[aGreyBlob] = [prevScale.greyBlobs[anIndex] for anIndex in greyIndices]


		
		prevScale_candidates = {}
		for aGreyBlob in prevScale.greyBlobs :
			# Find out which grey blobs exists at the current scale level at the location
			# of this grey blob's extremum. We automatically removed any UNMARKED as well.
			greyIndices = set([currScale.greyMarks[anIndex] for anIndex in aGreyBlob.extremum]) - ignoreThese

			prevScale_candidates[aGreyBlob] = [currScale.greyBlobs[anIndex] for anIndex in greyIndices]



		isAmbiguous = False
		for currGreyBlob, prevCandidates in currScale_candidates.iteritems() :
			if len(prevCandidates) > 2 :
				isAmbiguous = True
				break
			elif len(prevCandidates) == 2 :
				if (len(prevScale_candidates[prevCandidates[0]]) == 2 or
				    len(prevScale_candidates[prevCandidates[1]]) == 2) :
					isAmbiguous = True
					break

		if not isAmbiguous :
			for prevGreyBlob, currCandidates in prevScale_candidates.iteritems() :
				if len(currCandidates) > 2 :
					isAmbiguous = True
					break

		return isAmbiguous, {'currScale': currScale_candidates,
				     'prevScale': prevScale_candidates}



	def Link_GreyBlobs(self, candidates, currScale) :
		currScale_candidates = candidates['currScale']
		prevScale_candidates = candidates['prevScale']
		
		for (currGreyBlob, prevCandidates) in currScale_candidates.iteritems() :
			if len(prevCandidates) == 0 :
				# This is an absolutely brand-new scale blob!
				new_blob = ScaleSpace_Blob(self.currIDNum)
				new_event = new_blob.Start_ScaleBlob(currGreyBlob, currScale)

				Mark_ScaleBlob(currGreyBlob, currScale.scaleMarks, self.currIDNum)

				self.currIDNum += 1
				self.scaleBlobs_bright.append(new_blob)
				self.events_bright.append(new_event)

			elif len(prevCandidates) == 1 and len(prevScale_candidates[prevCandidates[0]]) == 1 :
					# It is only a continuation if the length of the corresponding candidate matching is one
					# Simple linkage
					theScaleBlob = prevCandidates[0].scaleBlob
					theScaleBlob.Continue_ScaleBlob(currGreyBlob, currScale)
					Mark_ScaleBlob(currGreyBlob, currScale.scaleMarks, theScaleBlob.idNum)

			elif len(prevCandidates) == 2 and (len(prevScale_candidates[prevCandidates[0]]) == 1 and
				    			   len(prevScale_candidates[prevCandidates[1]]) == 1) :
				# It is a merge only for certain linkages
				self.Merge_ScaleBlobs(currGreyBlob, currScale, [prevCandidates[0].scaleBlob,
										prevCandidates[1].scaleBlob])

			else :
				print "Degenerate situation? len(prevCandidates):", len(prevCandidates)
				new_blob = ScaleSpace_Blob(self.currIDNum)
                                new_event = new_blob.Start_ScaleBlob(currGreyBlob, currScale)

                                Mark_ScaleBlob(currGreyBlob, currScale.scaleMarks, self.currIDNum)

                                self.currIDNum += 1
                                self.scaleBlobs_bright.append(new_blob)
                                self.events_bright.append(new_event)


		for (prevGreyBlob, currCandidates) in prevScale_candidates.iteritems() :
			if len(currCandidates) == 0 :
				# This is an absolutely dead scale blob!
				end_event = prevGreyBlob.scaleBlob.End_ScaleBlob()
				self.events_bright.append(end_event)

			elif len(currCandidates) == 2 and (len(currScale_candidates[currCandidates[0]]) == 1 and
							   len(currScale_candidates[currCandidates[1]]) == 1) :
				# This is a split only for certain linkages.
				self.Split_ScaleBlob(currCandidates, currScale, prevGreyBlob.scaleBlob)





	def Split_ScaleBlob(self, greyBlobs, scaleLevel, scaleBlob) :
		splitEvent = Scale_Event(Scale_Event.SPLIT,
                                         [scaleBlob], [],
					 # Might need to change...
                                         scaleBlob.support_regions[-1].first_moment(),
                                         scaleLevel)

		newScaleBlobs = []
		for aGreyBlob in greyBlobs :
			Mark_ScaleBlob(aGreyBlob, scaleLevel.scaleMarks, self.currIDNum)

			newBlob = ScaleSpace_Blob(self.currIDNum)
			aGreyBlob.scaleBlob = newBlob
			newBlob.grey_blobs.append(aGreyBlob)
			newBlob.appearance = scaleLevel
			newBlob.disappearance = scaleLevel
			newBlob.support_regions.append(aGreyBlob.support_region)
                	newBlob.scale_levels.append(scaleLevel)
			newBlob.events.append(splitEvent)

			self.currIDNum += 1

			newScaleBlobs.append(newBlob)

		# TODO: Probably some more things I was supposed to do...
		splitEvent.scaleBlobs_below = newScaleBlobs

		scaleBlob.events.append(splitEvent)

		self.events_bright.append(splitEvent)
		self.scaleBlobs_bright += newScaleBlobs



	def Merge_ScaleBlobs(self, greyBlob, scaleLevel, scaleBlobs) :
		Mark_ScaleBlob(greyBlob, scaleLevel.scaleMarks, self.currIDNum)
		
		# Not exactly sure how we are going to represent it correctly,
		#     so we will get away with just creating a new blob for now
		newBlob = ScaleSpace_Blob(self.currIDNum)
		greyBlob.scaleBlob = newBlob
		newBlob.grey_blobs.append(greyBlob)		
		newBlob.appearance = scaleLevel
		newBlob.disappearance = scaleLevel
		newBlob.support_regions.append(greyBlob.support_region)
                newBlob.scale_levels.append(scaleLevel)

		self.currIDNum += 1

		mergeEvent = Scale_Event(Scale_Event.MERGE,
					 scaleBlobs, [newBlob],
                                       	 greyBlob.support_region.first_moment(),
					 scaleLevel)

		newBlob.events.append(mergeEvent)
		for aScaleBlob in scaleBlobs :
			aScaleBlob.events.append(mergeEvent)
					
		# TODO: end the other scale blobs!
		self.events_bright.append(mergeEvent)
		self.scaleBlobs_bright.append(newBlob)

