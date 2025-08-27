using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEngine;

public class UdpPoseReceiver : MonoBehaviour
{
    public int port = 5056;

    UdpClient _client;
    Thread _thread;
    readonly object _lock = new object();
    readonly List<string> _msgs = new List<string>();

    public RandomAvatarSpawner spawner;

    void Start()
    {
        if (spawner == null) spawner = FindObjectOfType<RandomAvatarSpawner>();
        try
        {
            _client = new UdpClient(port);
        }
        catch (Exception e)
        {
            Debug.LogError("UDP bind failed: " + e.Message);
            enabled = false; return;
        }
        _thread = new Thread(Listen) { IsBackground = true };
        _thread.Start();
    }

    void Listen()
    {
        IPEndPoint ep = new IPEndPoint(IPAddress.Any, port);
        while (true)
        {
            try
            {
                var data = _client.Receive(ref ep);
                var json = Encoding.UTF8.GetString(data);
                lock (_lock) { _msgs.Add(json); }
            }
            catch { /* ignore */ }
        }
    }

    void Update()
    {
        string msg = null;
        lock (_lock)
        {
            if (_msgs.Count > 0)
            {
                msg = _msgs[0];
                _msgs.RemoveAt(0);
            }
        }
        if (msg != null) ProcessJson(msg);
    }

    void ProcessJson(string json)
    {
        // gender & event
        string gender = "unknown";
        string evt = "none";
        var mG = Regex.Match(json, "\"gender\"\\s*:\\s*\"(?<g>[^\"]+)\"", RegexOptions.IgnoreCase);
        if (mG.Success) gender = mG.Groups["g"].Value.ToLower();

        var mE = Regex.Match(json, "\"event\"\\s*:\\s*\"(?<e>[^\"]+)\"", RegexOptions.IgnoreCase);
        if (mE.Success) evt = mE.Groups["e"].Value.ToLower();

        // bones:  { "Name":[x,y,z], ... }
        var bones = new Dictionary<string, float[]>();
        var ix = json.IndexOf("\"bones\"", StringComparison.OrdinalIgnoreCase);
        if (ix >= 0)
        {
            var bStart = json.IndexOf('{', ix);
            if (bStart >= 0)
            {
                int depth = 0;
                int i;
                for (i = bStart; i < json.Length; ++i)
                {
                    if (json[i] == '{') depth++;
                    else if (json[i] == '}') { depth--; if (depth == 0) break; }
                }
                if (i < json.Length)
                {
                    var bonesJson = json.Substring(bStart, i - bStart + 1);
                    var re = new Regex("\"(?<name>[A-Za-z0-9_]+)\"\\s*:\\s*\\[(?<vals>[^\\]]+)\\]");
                    var matches = re.Matches(bonesJson);
                    foreach (Match mm in matches)
                    {
                        var name = mm.Groups["name"].Value;
                        var vals = mm.Groups["vals"].Value.Split(',');
                        var list = new List<float>();
                        foreach (var s in vals)
                        {
                            float f;
                            if (float.TryParse(s, System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out f))
                                list.Add(f);
                        }
                        if (list.Count >= 3)
                            bones[name] = new float[] { list[0], list[1], list[2] };
                    }
                }
            }
        }

        if (spawner == null) spawner = FindObjectOfType<RandomAvatarSpawner>();
        if (spawner == null) return;

        if (evt == "entered") spawner.SpawnNew(gender);
        else if (evt == "left") spawner.Despawn();

        if (bones.Count > 0) spawner.ApplyBones(bones);
    }

    void OnDestroy()
    {
        try { _client?.Close(); } catch { }
        try { _thread?.Abort(); } catch { }
    }
}
