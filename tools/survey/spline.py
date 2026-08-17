#!/usr/bin/env python3
"""
Evaluate Minecraft cubic splines straight out of Terralith's JSON.

Terrain model (vanilla 1.18+ pipeline, which Terralith keeps):
    depth(y) = y_clamped_gradient(-64:1.5 -> 320:-1.5) + offset
    surface where 4*quarter_negative(depth*factor) + base_3d_noise == 0
  ignoring the 3d noise, depth == 0 gives
    y* = 128 * offset + 128,  and offset = spline - 0.50375
  so   y* ~= 128 * spline_value + 63.5
i.e. the offset spline reads directly as "height above sea level / 128".
"""
import json, bisect
import numpy as np


def _leaf(v):
    return isinstance(v, (int, float))


class Spline:
    def __init__(self, d):
        self.coord = d["coordinate"]
        pts = d["points"]
        self.loc = [p["location"] for p in pts]
        self.der = [p["derivative"] for p in pts]
        self.val = [p["value"] if _leaf(p["value"]) else Spline(p["value"])
                    for p in pts]

    def __call__(self, env):
        c = env[self.coord]
        n = len(self.loc)
        vals = [v if _leaf(v) else v(env) for v in self.val]
        i = bisect.bisect_left(self.loc, c) - 1
        if i < 0:
            return vals[0] + self.der[0] * (c - self.loc[0])
        if i >= n - 1:
            return vals[n-1] + self.der[n-1] * (c - self.loc[n-1])
        l0, l1 = self.loc[i], self.loc[i+1]
        t = (c - l0) / (l1 - l0)
        v0, v1 = vals[i], vals[i+1]
        d0 = self.der[i] * (l1 - l0) - (v1 - v0)
        d1 = -self.der[i+1] * (l1 - l0) + (v1 - v0)
        return (v0 + t*(v1-v0)) + t*(1-t)*(d0 + t*(d1-d0))


def find_spline(node):
    """pull the top-level spline out of a density-function json"""
    if isinstance(node, dict):
        if node.get("type", "").endswith("spline"):
            return Spline(node["spline"])
        for k in ("argument", "argument1", "argument2", "input"):
            if k in node:
                r = find_spline(node[k])
                if r is not None:
                    return r
    return None


def const_offset(node, acc=0.0):
    """the additive constant sitting in front of the offset spline"""
    if isinstance(node, dict):
        if node.get("type") == "minecraft:add":
            a1, a2 = node["argument1"], node["argument2"]
            if _leaf(a1):
                return const_offset(a2, acc + a1)
            if _leaf(a2):
                return const_offset(a1, acc + a2)
            for a in (a1, a2):
                r = const_offset(a, acc)
                if r != acc:
                    return r
        for k in ("argument", "argument1", "argument2", "input"):
            if k in node:
                r = const_offset(node[k], acc)
                if r != acc:
                    return r
    return acc


import os
TL = os.environ.get("TERRALITH_DIR", "./tl")
DF = f"{TL}/data/minecraft/worldgen/density_function/overworld"


def load(name):
    return json.load(open(f"{DF}/{name}.json"))


if __name__ == "__main__":
    for nm in ("offset", "factor", "jaggedness"):
        j = load(nm)
        s = find_spline(j)
        print(f"{nm}: root coordinate = {s.coord}, {len(s.loc)} points, "
              f"additive const = {const_offset(j):.6f}")
        # collect the coordinate names used anywhere in the tree
        seen = set()
        def walk(sp):
            seen.add(sp.coord)
            for v in sp.val:
                if isinstance(v, Spline):
                    walk(v)
        walk(s)
        print("   coordinates used:", sorted(seen))
