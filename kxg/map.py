class Node (object):

    UNSET_INDEX = -1

    def __init__(self, weight):
        self.index = Node.UNSET_INDEX
        self.weight = weight
        
        self.activate()

    def __repr__(self):
        return "<Node %s>" % self.get_index()

    def get_index(self):
        return self.index
    def get_weight(self):
        assert self.weight
        return self.weight

    def set_index(self, index):
        assert self.get_index() == Node.UNSET_INDEX
        self.index = index
    def set_weight(self, weight):
        self.weight = weight

    def is_active(self):
        return self.active

    def activate(self):
        self.active = True
    def deactivate(self):
        self.active = False


class Edge (object):

    def __init__(self, start, end, distance=1):
        self.set_nodes(start, end)
        self.set_distance(distance)

    def __repr__(self):
        return "<Edge: %s to %s>" % (self.get_start().get_index(), self.get_end().get_index())

    def is_active(self):
        return self.get_start().is_active() and self.get_end().is_active()

    def get_nodes(self):
        return (self.start, self.end)

    def set_nodes(self, start, end):
        self.start = start
        self.end = end

    def get_start(self):
        return self.start

    def get_end(self):
        return self.end

    def get_distance(self):
        return self.distance

    def get_cost(self):
        weight = self.get_start().get_weight() * self.get_end().get_weight()
        distance = self.get_distance()
        return weight * distance

    def set_start(self, start):
        self.start = start

    def set_end(self, end):
        self.end = end

    def set_distance(self, distance):
        self.distance = distance



class Graph (object):

    def __init__(self):
        self.nodes = []
        self.edges = {}

    def __iter__(self):
        for node in self.nodes:
            yield node

    def add_node(self, node):
        if node in self.nodes:
            message = "This node is already in the graph at position #%d."
            raise KeyError(message % self.nodes.index(node))

        index = len(self.nodes)
        node.set_index(index)
        self.nodes.append(node)

        return index

    def add_edge(self, edge):
        start = edge.get_start()
        end = edge.get_end()

        if start not in self.edges:
            self.edges[start] = {}
        if end not in self.edges[start]:
            self.edges[start][end] = edge

    def get_node(self, index):
        return self.nodes[index]

    def get_nodes(self):
        return self.nodes

    def get_num_nodes(self):
        return len(self.nodes)

    def get_index(self, node):
        return self.nodes.index(node)

    def index_exists(self, index):
        return index < len(self.nodes)

    def get_edges(self):
        return self.edges

    def get_edge(self, start, end):
        return self.edges[start][end]

    def get_edges_from(self, node):
        return self.edges[node].values()

    def get_all_edges(self):
        return [edge
                for node in self.get_edges()
                for edge in self.get_edges_from(node)]

    def get_num_edges(self):
        return len(self.get_all_edges())

    def get_neighbors(self, node, cache_ok=True):
        return (edge.get_end() for edge in self.get_edges_from(node))



class Grid (object):

    def __init__(self, rows, columns):
        self.rows, self.columns = rows, columns
        self.tiles = [None] * self.rows * self.columns

    def __getitem__(self, index):
        row, column = index
        return self.tiles[row * self.columns + column]

    def __setitem__(self, index, node):
        row, column = index
        self.tiles[row * self.columns + column] = node

    def make_graph(self):
        graph = Graph()

        # Add the nodes to the graph.
        for node in self.tiles:
            graph.add_node(node)

        # Add the edges to the graph.
        square = 1
        diagonal = sqrt(2) * square

        neighbors = [(-1, -1, diagonal), (0, -1, square), (1, -1, diagonal),
                     (-1, 0, square),                     (1, 0, square),
                     (-1, 1, diagonal),  (0, 1, square),  (1, 1, diagonal)]

        for y in range(self.rows):
            for x in range(self.columns):
                node = self[y, x]

                for fields in neighbors:
                    dx, dy, distance = fields
                    neighbor = self[y+dy, x+dx]

                    graph.add_edge(Edge(node, neighbor, distance))
                    graph.add_edge(Edge(neighbor, node, distance))




class PriorityQueue (object):

    def __init__(self, compare=lambda a, b: a < b):
        self.heap = []
        self.set = set()
        self.compare = compare

    def __len__(self):
        return len(self.heap)
    def __repr__(self):
        return str(self.heap)
    def __contains__(self, item):
        return item in self.set

    def push(self, item):
        self.heap.append(item)
        self.set.add(item)

        self._bubble(len(self) - 1)

    def update(self, item):
        index = self.heap.index(item)
        self._bubble(index)

    def pop(self):
        set = self.set
        heap = self.heap
        compare = self.compare

        size = len(self) - 1

        if not size:
            first = heap.pop()
        else:
            first = heap.pop(0)
            last = heap.pop()

            heap.insert(0, last)
            self._drip(0)

        set.remove(first)
        return first

    def peek(self):
        return self.heap[0]
    def empty(self):
        return len(self) == 0

    def _bubble(self, index):
        heap = self.heap
        compare = self.compare

        child = index
        parent = (child - 1) / 2

        while child and compare(heap[child], heap[parent]):
            heap[child], heap[parent] = heap[parent], heap[child]
            child, parent = parent, (parent - 1)/2

    def _drip(self, index):
        heap = self.heap
        compare = self.compare

        get_parent_child = lambda parent: (parent, 2 * parent + 1)
        parent, child = get_parent_child(index)

        size = len(self) - 1

        while child < size:
            if (child < size - 1) and compare(heap[child + 1], heap[child]):
                child += 1

            if compare(heap[child], heap[parent]):
                heap[child], heap[parent] = heap[parent], heap[child]
                parent, child = get_parent_child(child)
            else:
                break


class IndexedPQ (PriorityQueue):

    def __init__(self, weights, compare=lambda a, b: a < b):
        PriorityQueue.__init__(self, self._compare)
        self.weights = weights
        self.naive_compare = compare

    def _compare(self, a, b):
        weights = self.weights
        compare = self.naive_compare
        return compare(weights[a], weights[b])



class SearchAlgorithm (object):

    def __init__(self):
        self.routes = {}
        self.visited = {}

        self.found = False
        self.searching = False

        self.start_time = 0
        self.search_time = 0

    def __str__(self):
        return "[%s] Search Time: %f" % (self.get_name(), self.get_search_time())

    def is_searching(self):
        return self.searching

    def was_target_found(self):
        return self.found

    def get_search_time(self):
        return self.search_time

    def get_route(self):
        return self.route

    def get_routes(self):
        return self.routes

    def search(self, map):
        self.searching = True
        self.start_time = time.time()

    def target_found(self, routes, source, target):
        tile = target
        route = [tile]

        while tile != source:
            tile = routes[tile]
            route.append(tile)

        self.route = route
        self.routes = routes

        self.found = True
        self.searching = False
        self.search_time = time.time() - self.start_time

    def target_not_found(self, routes):
        self.route = []
        self.routes = routes

        self.found = False
        self.searching = False
        self.search_time = time.time() - self.start_time


class DepthFirstSearch (SearchAlgorithm):

    def search(self, map):
        SearchAlgorithm.search(self, map)

        source = map.get_source()
        target = map.get_target()

        routes = dict()
        visited = set()

        dummy = graph.Edge(source, source)
        edges = [dummy]
        
        while edges:
            edge = edges.pop()
            start = edge.get_start()
            end = edge.get_end()

            routes[end] = start
            visited.add(end)

            if end == target:
                self.target_found(routes, source, target)
                break

            # Use comprehensions for performance gains.
            new_edges = [ edge for edge in map.get_edges_from(end)
                          if edge.is_active()
                          if edge.get_end() not in visited ]
            edges += new_edges

        else:
            self.target_not_found(routes)


class BreadthFirstSearch (SearchAlgorithm):

    def search(self, map):
        SearchAlgorithm.search(self, map)

        source = map.get_source()
        target = map.get_target()

        routes = {}
        visited = set([source])

        dummy = graph.Edge(source, source)
        stack = [dummy]

        while stack:
            edge = stack.pop(0)
            start = edge.get_start()
            end = edge.get_end()

            routes[end] = start

            if end == target:
                self.target_found(routes, source, target)
                break

            for edge in map.get_edges_from(end):
                if not edge.is_active(): continue
                if edge.get_end() in visited: continue

                stack.append(edge)
                visited.add(edge.get_end())
        else:
            self.target_not_found(routes)


class A_Star (SearchAlgorithm):

    def __init__(self, heuristic):
        self.heuristic = heuristic

    def search(self, map):
        SearchAlgorithm.search(self, map)

        # Define variables in local scope
        source = map.get_source()
        target = map.get_target()

        routes = {}
        starting_nodes = {source: source}

        real_costs = {source: 0}
        estimated_costs = {source: 0}

        frontier_nodes = IndexedPQ(estimated_costs)
        frontier_nodes.push(source)

        heuristic = self.heuristic

        # Loop through the graph
        while not frontier_nodes.empty():
            closest_node = frontier_nodes.pop()
            routes[closest_node] = starting_nodes[closest_node]

            # Check if the target was found
            if closest_node == target:
                self.target_found(routes, source, target)
                break

            # Add more edges to consider
            edges_from = map.expand_node(closest_node)
            if not edges_from:
                edges_from = map.get_edges_from(closest_node)

            for edge in edges_from:
                if not edge.is_active(): continue
                if edge.get_end() in routes: continue

                start = edge.get_start()
                end = edge.get_end()

                real_cost = real_costs[start] + edge.get_cost()
                heuristic_cost = heuristic(end, target)

                if end in frontier_nodes:
                    # Already considering this node; choose the shortest path:
                    if real_cost < real_costs[end]:
                        real_costs[end] = real_cost
                        estimated_costs[end] = real_cost + heuristic_cost

                        starting_nodes[end] = start
                        frontier_nodes.update(end)
                else:
                    # Haven't been here before; store the edge:
                    real_costs[end] = real_cost
                    estimated_costs[end] = real_cost + heuristic_cost

                    starting_nodes[end] = start
                    frontier_nodes.push(end)
        else:
            self.target_not_found(routes)


class Dijkstra (A_Star):

    def __init__(self):
        A_Star.__init__(self, lambda start, end: 0)
