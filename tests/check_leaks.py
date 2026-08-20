import sqlite3
import subprocess

def check_resources():
    conn = sqlite3.connect("lambdax.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Over-provisioning check
    cursor.execute("SELECT id, name, max_containers FROM functions")
    functions = cursor.fetchall()
    
    for f in functions:
        cursor.execute("SELECT COUNT(*) as c FROM containers WHERE function_id = ? AND state != 'REMOVED'", (f['id'],))
        active = cursor.fetchone()['c']
        
        if active > f['max_containers']:
            print(f"FAIL: Over-provisioning detected! Function {f['name']} has {active} active containers (max {f['max_containers']})")
        else:
            print(f"PASS: No over-provisioning for {f['name']} ({active} <= {f['max_containers']})")
            
    # 2. Resource leak check
    # Get all active containers in DB that should have a docker container running
    cursor.execute("SELECT container_id FROM containers WHERE state IN ('IDLE', 'BUSY', 'STARTING') AND container_id != ''")
    db_containers = set([r['container_id'] for r in cursor.fetchall()])
    
    # Get actual docker containers
    try:
        docker_out = subprocess.check_output(["docker", "ps", "-q"]).decode('utf-8').strip().split('\n')
        docker_containers = set([c.strip() for c in docker_out if c.strip()])
    except:
        docker_containers = set()
        
    # Check if there are docker containers not in DB, or DB containers not in Docker
    # Note: DB stores full IDs usually, docker ps -q gives short IDs. Let's compare starts.
    db_short = set([c[:12] for c in db_containers])
    docker_short = set([c[:12] for c in docker_containers])
    
    untracked_docker = docker_short - db_short
    missing_docker = db_short - docker_short
    
    if untracked_docker:
        print(f"FAIL: Resource leak! Docker containers running not tracked in DB: {untracked_docker}")
    else:
        print("PASS: No untracked docker containers.")
        
    if missing_docker:
        print(f"FAIL: DB out of sync! DB thinks these are running but Docker disagrees: {missing_docker}")
    else:
        print("PASS: DB and Docker are perfectly synced.")
        
    conn.close()

if __name__ == "__main__":
    check_resources()
