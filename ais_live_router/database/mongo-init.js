db = db.getSiblingDB("aisdb");

db.vessels.createIndex({ "location": "2dsphere" });

// db.vessels.insertOne({
//   mmsi: 123456789,
//   location: {
//     type: "Point",
//     coordinates: [12.34, 56.78]  // [lon, lat]
//   },
//   timestamp: new Date(),
//   msg_type: 1
// });


// db.createUser({
//     user: "admin",
//     pwd: "adminpass",
//     roles: [{ role: "readWrite", db: "mydb" }]
//   });
  