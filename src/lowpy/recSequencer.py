import pychronos

class recSequencer(pychronos.sequencer):
    def __init__(self):
        super().__init__()

    def recordCountFrames(self, nFrames, **kwargs):
        if (self.status & 1):
            raise ValueError("Sequencer currently busy")

        program = pychronos.seqcommand()
        
        program.blockSize = nFrames
        program.blkTermFull = True
        program.recTermBlockEnd = True

        self.seqprogram[0] = program

        self.control = 2
        while(self.status & 1): pass
        self.control = 0

