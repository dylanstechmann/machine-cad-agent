"""Conservative box pruning followed by exact B-rep intersection volumes."""

OVERLAP_LIMIT_MM3 = .001
LIMB_PREFIXES = ("upper_","fore_","tool_","jaw_","thigh_","shin_","foot_")


class CollisionChecker:
    def __init__(self):
        self.world_cache = {}
        self.pair_cache = {}
        self.exact_intersections = 0
        self.box_pruned = 0

    def world(self,part):
        key = (part.name,part.loc.toTuple())
        if key not in self.world_cache:
            shape = part.world()
            self.world_cache[key] = shape,shape.BoundingBox()
        return key,self.world_cache[key]

    def overlap(self,a,b):
        ka,(sa,ba) = self.world(a)
        kb,(sb,bb) = self.world(b)
        key = (ka,kb)
        if key in self.pair_cache: return self.pair_cache[key]
        separated = any(min(getattr(ba,axis+"max"),getattr(bb,axis+"max"))-
                        max(getattr(ba,axis+"min"),getattr(bb,axis+"min"))<=0 for axis in "xyz")
        if separated:
            self.box_pruned += 1
            volume = 0.0
        else:
            self.exact_intersections += 1
            volume = sa.intersect(sb).Volume()
        self.pair_cache[key] = volume
        return volume

    def check(self,posed):
        physical = [p for p in posed if p.category!="visualization"]
        body = [p for p in physical if p.group=="body" and not p.name.startswith("shoulder_mount_") and p.name!="hip_bridge"]
        stationary = [p for p in physical if p.group=="stationary"]
        objects = [p for p in physical if p.group.startswith("object_")]
        limbs = [p for p in physical if p.group.startswith(LIMB_PREFIXES)]
        pairs = []
        for limb in limbs:
            pairs.extend((limb,p) for p in (*body,*stationary,*objects))
        for obj in objects:
            pairs.extend((obj,p) for p in (*body,*stationary))
        # Two-hand/object interference is meaningful; parts of the same object mate intentionally.
        for i,a in enumerate(objects):
            pairs.extend((a,b) for b in objects[i+1:] if a.group!=b.group)
        worktop = next(p for p in stationary if p.name=="worktop")
        pairs.extend((p,worktop) for p in physical if p.group=="body")
        failures = []
        for a,b in pairs:
            volume = self.overlap(a,b)
            if volume>OVERLAP_LIMIT_MM3:
                failures.append({"parts":[a.name,b.name],"overlap_mm3":round(volume,4)})
        return failures

    def stats(self):
        return {"exact_intersections":self.exact_intersections,"box_pruned_pairs":self.box_pruned,
                "cached_pair_results":len(self.pair_cache),"overlap_failure_threshold_mm3":OVERLAP_LIMIT_MM3}
