using System.Collections.Generic;
using UnityEngine;

public class RandomAvatarSpawner : MonoBehaviour
{
    public Transform SpawnRoot;
    public Vector3 SpawnPosition = Vector3.zero;
    public Vector3 SpawnEuler = new Vector3(0, 180, 0);
    public float Scale = 1.0f;

    GameObject[] malePrefabs;
    GameObject[] femalePrefabs;

    GameObject _current;
    AvatarRetarget _retarget;

    void Start()
    {
        malePrefabs = Resources.LoadAll<GameObject>("Avatars/Male");
        femalePrefabs = Resources.LoadAll<GameObject>("Avatars/Female");
        if ((malePrefabs == null || malePrefabs.Length == 0) &&
            (femalePrefabs == null || femalePrefabs.Length == 0))
        {
            Debug.LogWarning("No avatars found in Resources/Avatars/Male or /Female");
        }
    }

    public void SpawnNew(string gender)
    {
        Despawn();
        var pool = (gender == "female") ? femalePrefabs : malePrefabs;
        if (pool == null || pool.Length == 0)
        {
            Debug.LogWarning("No prefabs for gender: " + gender + " — falling back to male.");
            pool = malePrefabs;
            if (pool == null || pool.Length == 0) return;
        }

        var prefab = pool[Random.Range(0, pool.Length)];
        var parent = SpawnRoot ? SpawnRoot : transform;
        _current = Instantiate(prefab, parent);
        _current.transform.localPosition = SpawnPosition;
        _current.transform.localEulerAngles = SpawnEuler;
        _current.transform.localScale = Vector3.one * Scale;

        _retarget = _current.GetComponentInChildren<AvatarRetarget>();
        if (_retarget == null) _retarget = _current.AddComponent<AvatarRetarget>();
    }

    public void Despawn()
    {
        if (_current) Destroy(_current);
        _current = null; _retarget = null;
    }

    public void ApplyBones(Dictionary<string, float[]> bones)
    {
        if (_retarget != null && bones != null && bones.Count > 0)
            _retarget.ApplyBones(bones);
    }
}
