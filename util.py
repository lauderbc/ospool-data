import os
import json

import htcondor
import pickle
from pathlib import Path


def write_document_to_file(
        document,
        directory: str,
        path: str,
        overwrite: bool = False
):
    """Write a daily file into a data directory"""

    output_path = f"{directory}/{path}"

    if overwrite or not os.path.isfile(output_path):
        with open(output_path, "w") as fp:
            json.dump(document, fp)

OSPOOL_COLLECTORS = {
    "cm-1.ospool.osg-htc.org",
    "cm-2.ospool.osg-htc.org",
    "flock.opensciencegrid.org",
}

def get_ospool_aps():
    aps = set()
    ap_collector_host_map = get_schedd_collector_host_map()
    for ap, collectors in ap_collector_host_map.items():
        if ap.startswith("jupyter-notebook-") or ap.startswith("jupyterlab-"):
            continue
        if len(collectors & OSPOOL_COLLECTORS) > 0:
            aps.add(ap)
    return aps

OSPOOL_NON_FAIRSHARE_RESOURCES = {
    "SURFsara",
    "NIKHEF-ELPROD",
    "INFN-T1",
    "IN2P3-CC",
    "UIUC-ICC-SPT",
    "TACC-Frontera-CE2",
}

CUSTOM_MAPPING = {
    "osg-login2.pace.gatech.edu": {"osg-login2.pace.gatech.edu"},
    "ce1.opensciencegrid.org": {"cm-2.ospool.osg-htc.org", "cm-1.ospool.osg-htc.org"},
    "login-test.osgconnect.net": {"cm-2.ospool.osg-htc.org", "cm-1.ospool.osg-htc.org"},
    "scosg16.jlab.org": {"scicollector.jlab.org", "osg-jlab-1.t2.ucsd.edu"},
    "scosgdev16.jlab.org": {"scicollector.jlab.org", "osg-jlab-1.t2.ucsd.edu"},
    "submit6.chtc.wisc.edu": {"htcondor-cm-path.osg.chtc.io"},
    "login-el7.xenon.ci-connect.net": {"cm-2.ospool.osg-htc.org", "cm-1.ospool.osg-htc.org"},
    "login.collab.ci-connect.net": {"cm-2.ospool.osg-htc.org", "cm-1.ospool.osg-htc.org"},
    "uclhc-2.ps.uci.edu": {"uclhc-2.ps.uci.edu"},
    "osgsub01.sdcc.bnl.gov": {"scicollector.jlab.org", "osg-jlab-1.t2.ucsd.edu"},
}


def get_schedd_collector_host_map():

    collector_host = "cm-1.ospool.osg-htc.org"
    collector_hosts = {"cm-1.ospool.osg-htc.org", "cm-2.ospool.osg-htc.org"}
    schedd_collector_host_map_pickle = Path("ospool-host-map.pkl")
    schedd_collector_host_map = {}
    if schedd_collector_host_map_pickle.exists():
        try:
            schedd_collector_host_map = pickle.load(open(schedd_collector_host_map_pickle, "rb"))
        except IOError:
            pass
    schedd_collector_host_map.update(CUSTOM_MAPPING)

    collector = htcondor.Collector(collector_host)
    schedds = [ad["Machine"] for ad in collector.locateAll(htcondor.DaemonTypes.Schedd)]

    for schedd in schedds:
        schedd_collector_host_map[schedd] = set()

        for collector_host in collector_hosts:
            collector = htcondor.Collector(collector_host)
            ads = collector.query(
                htcondor.AdTypes.Schedd,
                constraint=f'''Machine == "{schedd.split('@')[-1]}"''',
                projection=["Machine", "CollectorHost"],
            )
            ads = list(ads)
            if len(ads) == 0:
                continue
            if len(ads) > 1:
                print(f'Got multiple Schedd ClassAds for Machine == "{schedd}"')

            # Cache the CollectorHost in the map
            if "CollectorHost" in ads[0]:
                schedd_collector_hosts = set()
                for schedd_collector_host in ads[0]["CollectorHost"].split(","):
                    schedd_collector_host = schedd_collector_host.strip().split(":")[0]
                    if schedd_collector_host:
                        schedd_collector_hosts.add(schedd_collector_host)
                if schedd_collector_hosts:
                    schedd_collector_host_map[schedd] = schedd_collector_hosts
                    break
        else:
            print(f"Did not find Machine == {schedd} in collectors")

    # Update the pickle
    with open(schedd_collector_host_map_pickle, "wb") as f:
        pickle.dump(schedd_collector_host_map, f)

    return schedd_collector_host_map

if __name__ == "__main__":
    get_schedd_collector_host_map()