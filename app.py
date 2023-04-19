# This file draws a gui for the user to interact with the program
# It also contains the main function that runs the program

import multiprocessing
import PySimpleGUI as sg
import platform  # For getting the operating system name
import subprocess  # For executing a shell command
import paramiko
import os

# import creds.txt if it exists
if os.path.exists("creds.txt"):
    with open("creds.txt", "r") as f:
        hosts = f.read().splitlines()
else:
    hosts = []


def addHosts(host):
    if host not in hosts:
        hosts.append(host)


def ping(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if the host name is valid.
    """

    # Option for the number of packets as a function of
    param = "-n" if platform.system().lower() == "windows" else "-c"

    # Building the command. Ex: "ping -c 1 google.com"
    command = ["ping", param, "1", host]

    return subprocess.call(command) == 0


def drawElement(element, hPosition, vPosition):
    if hPosition == "left":
        hElement = [element, sg.Stretch()]
    elif hPosition == "right":
        hElement = [sg.Stretch(), element]
    else:
        hElement = [sg.Stretch(), element, sg.Stretch()]
    if vPosition == "top":
        vElement = [[hElement], [sg.VStretch()]]
    elif vPosition == "bottom":
        vElement = [[sg.VStretch()], [hElement]]
    else:
        vElement = [[sg.VStretch()], [hElement], [sg.VStretch()]]
    return vElement


def hCenterElement(element):
    return [sg.Stretch(), element, sg.Stretch()]


def vCenterElement(element):
    return [[sg.VStretch()], [element], [sg.VStretch()]]


def getComputers(query):
    if "-" not in query and "/" not in query:
        # assume single ip
        addHosts(query)
    elif "/" in query:
        print("cidr notation is not implemented yet")
    elif "-" in query:
        query = query.split("-")
        # check if value after dash has periods
        start = int(query[0].split(".")[-1])
        if "." in query[1]:
            # get first 3 octets of start
            print("multi-subnet scanning not implemented yet")
        else:
            end = int(query[1])
        for i in range(start, end + 1):
            host = ".".join(query[0].split(".")[0:-1] + [str(i)])
            addHosts(host)
    return hosts


def ping(ip):
    TIMEOUT = 2  # in seconds
    """ Returns true iff the host is reachable. """
    # print('ping %s' % ip)  # uncomment to see progress
    ret = subprocess.call(
        ["ping", "-W", str(TIMEOUT), "-c", "1", ip], stdout=subprocess.DEVNULL
    )
    if ret == 0:
        return True


def ssh(data):
    # get ip, username, password, and command from tuple
    ip = data[0]
    username = data[1]
    password = data[2]
    command = data[3]
    port = 22
    # create ssh client
    client = paramiko.SSHClient()
    # add to known hosts
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # connect to host
    client.connect(ip, port, username, password)
    # run command
    stdin, stdout, stderr = client.exec_command(command)
    # print output
    if stdout is not None:
        result = stdout.read().decode("utf-8")
        # write ip, username, password to file
        # if creds.txt does not exist, create it
        if not os.path.exists("creds.txt"):
            with open("creds.txt", "w") as f:
                f.write("")
        # if ip is not in creds.txt, append it
        with open("creds.txt", "r") as f:
            if ip not in f.read():
                with open("creds.txt", "a") as f:
                    f.write(ip + "\n")
    # close connection
    client.close()
    return [username + "@" + ip, result]


def getCommand():
    # get command from user
    command = sg.popup_get_text("Enter command to run on computers")
    return command


def pingAll(ips):
    computers = []
    if len(ips) < 100:
        CONCURRENCY = len(ips)
    else:
        CONCURRENCY = 100
    with multiprocessing.Pool(CONCURRENCY) as p:
        uplist = p.map(ping, ips)
        # append to ip to computers where uplist is true
        for i in range(len(uplist)):
            if uplist[i]:
                computers.append(ips[i])
    return computers


def multiSSH(ips, username, password, command):
    # if ips is a string, convert it to an array
    if type(ips) == str:
        ips = [ips]
    # if ips length is < 100, set CONCURRENCY to ips length
    if len(ips) < 100:
        CONCURRENCY = len(ips)
    else:
        CONCURRENCY = 100
    # turn ips array into an array of arrays
    ips = [[ip, username, password, command] for ip in ips]
    with multiprocessing.Pool(CONCURRENCY) as p:
        res = p.map(ssh, ips)
    return res


def getCreds(username="", password=""):
    # pop up window asking for username and password. Hide password
    layout = [
        hCenterElement(sg.Text("Enter username")),
        hCenterElement(sg.Input(username, key="username")),
        hCenterElement(sg.Text("Enter password")),
        hCenterElement(sg.Input(password, key="password", password_char="*")),
        [
            sg.Stretch(),
            sg.Button("Submit", bind_return_key=True),
            sg.Stretch(),
            sg.Button("Cancel"),
            sg.Stretch(),
        ],
    ]
    window = sg.Window(
        "Enter Credentials", layout, default_element_size=(12, 1)
    )  # this is the chang
    while True:
        event, values = window.read()
        if event == "Submit":
            # print highlighted value in listbox
            # close window
            window.close()
            return [values["username"], values["password"]]
        if event == "Cancel":
            window.close()
            return [None, None]
        if event == sg.WIN_CLOSED:
            return [None, None]


def processOutput(input):
    output = []
    # input is an array of arrays
    # each array is [ip, output]
    # output is a string
    # split output into lines
    for i in input:
        output.append(i[0])
        output.append("-----------")
        output.append(i[1])
        output.append("\n")
    return output


def main():
    username = ""
    password = ""
    layout = [
        hCenterElement(sg.Text("Unix Remote Desktop")),
        [
            sg.Stretch(),
            sg.Text(
                "Enter Subnet to search across (ex:192.168.1.1-255)"
            ),  # 10.26.9.1-10.26.9.4
        ],
        [sg.Stretch(), sg.Input(size=(25, 1), key="path")],
        [sg.Stretch(), sg.Button("Search", bind_return_key=True)],
        [sg.Stretch(), sg.Text("Select a computer to connect to"), sg.Stretch()],
        [
            sg.Stretch(),
            sg.Listbox(
                values=hosts, size=(40, 20), key="listbox", select_mode="extended"
            ),
            sg.Stretch(),
        ],
        drawElement(sg.Button("Connect"), "right", "bottom"),
    ]

    window = sg.Window(
        "Unix Remote Desktop",
        layout,
        default_element_size=(12, 1),
        resizable=True,
        finalize=True,
    )  # this is the chang
    window.bind("<Configure>", "Event")

    while True:
        event, values = window.read()
        if event == "Connect":
            command = getCommand()
            # print highlighted value in listbox
            comp = values["listbox"]
            # attempt to ssh into the computer
            # Create popup_scrolled window with no input

            [username, password] = getCreds(username, password)
            if username != None and password != None:
                res = multiSSH(comp, username, password, command)
                # display message containing res
                sg.popup_scrolled(*processOutput(res), title="Result")
        if event == "Search":
            computers = pingAll(getComputers(values["path"]))
            window["listbox"].update(values=computers)
        if event == sg.WIN_CLOSED:
            break


if __name__ == "__main__":
    main()
