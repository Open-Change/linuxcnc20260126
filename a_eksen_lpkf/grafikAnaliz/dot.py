#!/usr/bin/python3
#    This is a component of emc2
#    Copyright 2007 Jeff Epler <jepler@unpythonic.net>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os
import sys
import subprocess
import re

def to_dot_name(s):
    return re.sub("[^a-zA-Z0-9_]+", "_", s)

def port(s):
    return s.rsplit(".", 1)[0]

def leaf(s):
    if "." in s:
        return s.rsplit(".", 1)[1]
    else:
        return s

def to_leaf_name(s):
    if "." in s:
        return to_dot_name(s.rsplit(".", 1)[1])
    else:
        return to_dot_name(s)

def to_port_name(s):
    return to_dot_name(s.rsplit(".", 1)[0])

def to_node_name(s):
    if "." in s:
        return "%s:%s" % (to_port_name(s), to_leaf_name(s))
    else:
        n = to_dot_name(s)
        return "%s:%s" % (n, n)

def direction(s):
    if s in directions:
        return directions[s]
    o = subprocess.getoutput("halcmd -s show pin %s" % s)
    if "IO" in o:
        return "both"
    if "OUT" in o:
        return 0
    if "IN" in o:
        return 1
    return "none"

print("digraph net {")
print("    node [shape=record];")
directions = {}
nodes = {}
edges = set()
signals = set()

def learn_direction(words):
    last = None
    dir = None
    for word in words:
        if word.startswith("<") and word.endswith(">"):
            dir = "both"
            if last:
                directions[last] = "both"
        elif word.startswith("<"):
            dir = 0
            if last:
                directions[last] = 1
        elif word.startswith("="):
            dir = 1
            if last:
                directions[last] = 0
        elif dir is not None:
            directions[word] = dir
            dir = None
        last = word

def print_signal(sig):
    if sig in signals:
        return
    signals.add(sig)
    ns = "sig_" + to_dot_name(sig)
    print("    %s [shape=diamond, label=\"%s\"]" % (ns, sig))

def handle_net(words):
    sig = words[1]

    print_signal(sig)

    for pin in words[2:]:
        handle_linkps(pin, sig)

def handle_linkps(pin, sig):
    print_signal(sig)
    nw = to_node_name(pin)
    ns = "sig_" + to_dot_name(sig)
    pn = port(pin)
    if pn in nodes:
        nodes[pn].append(pin)
    else:
        nodes[pn] = [pin]
    d = direction(pin)
    if d == "both":
        edges.add((ns, nw, "both", 2))
    elif d == "none":
        edges.add((ns, nw, "none", 2))
    elif d:
        edges.add((ns, nw, "forward", 1))
    else:
        edges.add((nw, ns, "forward", 3))

def input():
    if len(sys.argv) == 1:
        for line in os.popen("halcmd save netl"):
            yield line
    else:
        for arg in sys.argv[1:]:
            if arg == "-":
                source = sys.stdin
            else:
                source = open(arg)
            for line in source:
                yield line

for line in input():
    words = line.split()
    learn_direction(words)

    words = [w for w in words if w[0] not in "<="]
    if not words:
        continue
    if words[0] == "net":
        handle_net(words)
    elif words[0] == "linkps":
        handle_linkps(words[1], words[2])
    elif words[0] == "linksp":
        handle_linkps(words[2], words[1])
    elif words[0] == "linkpp":
        handle_linkps(words[1], words[1])
        handle_linkps(words[2], words[1])

print()
for n, v in nodes.items():
    label = "|".join("<%s>%s" % (to_leaf_name(i), leaf(i))
                     for i in sorted(v) if i != n)
    dn = to_dot_name(n)
    if label:
        print("    %s [label=\"<%s>%s|%s\"];" % (dn, dn, n, label))
    else:
        print("    %s [label=\"<%s>%s\"];" % (dn, dn, n))

print()
for a, b, c, d in edges:
    print("    %s -> %s" % (a, b), end="")
    if c or d:
        print(" [", end="")
        if c:
            print("dir=%s" % c, end="")
        if c and d:
            print(",", end="")
        if d:
            print("weight=%s" % d, end="")
        print("]", end="")
    print(";")

print("}")
