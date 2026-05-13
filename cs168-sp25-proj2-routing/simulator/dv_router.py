"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        ##### Begin Stage 10A #####
        self.history = {}
        ##### End Stage 10A #####

    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        ##### Begin Stage 1 #####
        self.table[host] = TableEntry(dst=host, port=port, latency=self.ports.get_latency(port), expire_time=FOREVER)
        ##### End Stage 1 #####

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        
        ##### Begin Stage 2 #####
        dst_host = packet.dst
        if dst_host in self.table:
            out_entry = self.table[dst_host]
            out_port = out_entry.port
            if out_entry.latency < INFINITY:
                self.send(packet, out_port)
        ##### End Stage 2 #####

    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        
        ##### Begin Stages 3, 6, 7, 8, 10 #####
        #告知端口p自己可以到dst，和latency
        for _, entry in self.table.items():
            for p in self.ports.get_all_ports():
                if single_port is not None and single_port != p:
                    continue

                send = False
                dst = entry.dst

                if self.POISON_REVERSE == True and p == entry.port:
                    latency = INFINITY
                    send = True

                elif self.SPLIT_HORIZON == False or p != entry.port:
                    latency = min(entry.latency, INFINITY)
                    send = True

                if force == False and p in self.history.keys() and dst in self.history[p].keys() and latency == self.history[p][dst]:
                    send = False
                
                if send:
                    self.send_route(p, dst, latency)
                    if p not in self.history.keys():
                        self.history[p] = {}
                    self.history[p][dst] = latency

                

        ##### End Stages 3, 6, 7, 8, 10 #####

    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        
        ##### Begin Stages 5, 9 #####
        expired_routes = []
        for dst in self.table.keys():
            if api.current_time() >= self.table[dst].expire_time:
                expired_routes.append(dst)

        for route in expired_routes:
            if self.POISON_EXPIRED == True:
                self.table[route] = TableEntry(dst=route, port=self.table[route].port, latency=INFINITY, expire_time=api.current_time()+self.ROUTE_TTL)
                self.log(f"A expired route to {route} is poisoned")
            else:    
                self.table.pop(route)
                self.log(f"A expired route to {route} is deleted")
        ##### End Stages 5, 9 #####

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        
        ##### Begin Stages 4, 10 #####
        port_latency = self.ports.get_latency(port)
        update_table = False
        if route_dst not in self.table.keys():
            update_table = True
            
        elif port == self.table[route_dst].port:
            update_table = True
        
        elif route_latency+port_latency < self.table[route_dst].latency:
            update_table = True
        
        if update_table:
            self.table[route_dst] = TableEntry(dst=route_dst, port=port, latency=route_latency+port_latency, expire_time=api.current_time()+self.ROUTE_TTL)
            self.send_routes(force=False)
        ##### End Stages 4, 10 #####

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        ##### Begin Stage 10B #####
        if self.handle_link_up:
            self.send_routes(single_port=port)

        ##### End Stage 10B #####

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router goes down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)

        ##### Begin Stage 10B #####
        if self.POISON_ON_LINK_DOWN:
            self.add_poison_to_port(port)

        else:
            self.del_port_route(port)
        ##### End Stage 10B #####

    # Feel free to add any helper methods!

    def add_poison_to_port(self, port):
        for h in self.table.keys():
            p = self.table[h].port
            expire_time = self.table[h].expire_time
            if port == p:
                self.table[h] = TableEntry(dst=h, port=p, latency=INFINITY, expire_time=expire_time)
            self.send_routes(force=False)

    def del_port_route(self, port):
        del_route = []
        for h in self.table.keys():
            if self.table[h].port == port:
                del_route.append(h)

        for h in del_route:
            self.table.pop(h)