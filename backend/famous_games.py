"""A curated base of famous games for the pre-reviewed library.

Each entry stores plain *movetext* (no PGN headers) plus display metadata. The
build step (`python -m backend.build_library`) assembles a full PGN from the
metadata, reviews the game with Stockfish, and writes the result to
`backend/data/library/`. The frontend then browses these instant, ready-made
reviews — no engine run required at view time.

Move transcriptions are validated during the build (games whose movetext fails
to parse cleanly are reported and skipped), so this list is self-checking.
"""

from __future__ import annotations

FAMOUS_GAMES: list[dict] = [
    {
        "id": "opera-game-1858",
        "white": "Paul Morphy",
        "black": "Duke Karl / Count Isouard",
        "event": "Paris Opera",
        "year": 1858,
        "result": "1-0",
        "nickname": "The Opera Game",
        "description": "Morphy's immortal miniature, played in a box at the opera — "
                       "rapid development and a clean queen-sacrifice mate.",
        "moves": "1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 "
                 "7. Qb3 Qe7 8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 "
                 "13. Rxd7 Rxd7 14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8#",
    },
    {
        "id": "immortal-game-1851",
        "white": "Adolf Anderssen",
        "black": "Lionel Kieseritzky",
        "event": "London",
        "year": 1851,
        "result": "1-0",
        "nickname": "The Immortal Game",
        "description": "Anderssen sacrifices a bishop, both rooks and the queen to "
                       "deliver mate with three minor pieces.",
        "moves": "1. e4 e5 2. f4 exf4 3. Bc4 Qh4+ 4. Kf1 b5 5. Bxb5 Nf6 6. Nf3 Qh6 "
                 "7. d3 Nh5 8. Nh4 Qg5 9. Nf5 c6 10. g4 Nf6 11. Rg1 cxb5 12. h4 Qg6 "
                 "13. h5 Qg5 14. Qf3 Ng8 15. Bxf4 Qf6 16. Nc3 Bc5 17. Nd5 Qxb2 18. Bd6 Bxg1 "
                 "19. e5 Qxa1+ 20. Ke2 Na6 21. Nxg7+ Kd8 22. Qf6+ Nxf6 23. Be7#",
    },
    {
        "id": "evergreen-game-1852",
        "white": "Adolf Anderssen",
        "black": "Jean Dufresne",
        "event": "Berlin",
        "year": 1852,
        "result": "1-0",
        "nickname": "The Evergreen Game",
        "description": "Anderssen's 'evergreen' brilliancy, crowned by a famous "
                       "queen sacrifice and a bishop-and-rook mating net.",
        "moves": "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. b4 Bxb4 5. c3 Ba5 6. d4 exd4 "
                 "7. O-O d3 8. Qb3 Qf6 9. e5 Qg6 10. Re1 Nge7 11. Ba3 b5 12. Qxb5 Rb8 "
                 "13. Qa4 Bb6 14. Nbd2 Bb7 15. Ne4 Qf5 16. Bxd3 Qh5 17. Nf6+ gxf6 18. exf6 Rg8 "
                 "19. Rad1 Qxf3 20. Rxe7+ Nxe7 21. Qxd7+ Kxd7 22. Bf5+ Ke8 23. Bd7+ Kf8 24. Bxe7#",
    },
    {
        "id": "game-of-the-century-1956",
        "white": "Donald Byrne",
        "black": "Robert James Fischer",
        "event": "Rosenwald, New York",
        "year": 1956,
        "result": "0-1",
        "nickname": "The Game of the Century",
        "description": "A 13-year-old Fischer unleashes the stunning ...Be6!! queen "
                       "offer and a windmill to defeat a leading American master.",
        "moves": "1. Nf3 Nf6 2. c4 g6 3. Nc3 Bg7 4. d4 O-O 5. Bf4 d5 6. Qb3 dxc4 "
                 "7. Qxc4 c6 8. e4 Nbd7 9. Rd1 Nb6 10. Qc5 Bg4 11. Bg5 Na4 12. Qa3 Nxc3 "
                 "13. bxc3 Nxe4 14. Bxe7 Qb6 15. Bc4 Nxc3 16. Bc5 Rfe8+ 17. Kf1 Be6 18. Bxb6 Bxc4+ "
                 "19. Kg1 Ne2+ 20. Kf1 Nxd4+ 21. Kg1 Ne2+ 22. Kf1 Nc3+ 23. Kg1 axb6 24. Qb4 Ra4 "
                 "25. Qxb6 Nxd1 26. h3 Rxa2 27. Kh2 Nxf2 28. Re1 Rxe1 29. Qd8+ Bf8 30. Nxe1 Bd5 "
                 "31. Nf3 Ne4 32. Qb8 b5 33. h4 h5 34. Ne5 Kg7 35. Kg1 Bc5+ 36. Kf1 Ng3+ "
                 "37. Ke1 Bb4+ 38. Kd1 Bb3+ 39. Kc1 Ne2+ 40. Kb1 Nc3+ 41. Kc1 Rc2#",
    },
    {
        "id": "kasparov-topalov-1999",
        "white": "Garry Kasparov",
        "black": "Veselin Topalov",
        "event": "Hoogovens, Wijk aan Zee",
        "year": 1999,
        "result": "1-0",
        "nickname": "Kasparov's Immortal",
        "description": "Kasparov's astonishing rook sacrifice on d4 launches a king "
                       "hunt that drags Topalov's king from a7 to d1.",
        "moves": "1. e4 d6 2. d4 Nf6 3. Nc3 g6 4. Be3 Bg7 5. Qd2 c6 6. f3 b5 7. Nge2 Nbd7 "
                 "8. Bh6 Bxh6 9. Qxh6 Bb7 10. a3 e5 11. O-O-O Qe7 12. Kb1 a6 13. Nc1 O-O-O "
                 "14. Nb3 exd4 15. Rxd4 c5 16. Rd1 Nb6 17. g3 Kb8 18. Na5 Ba8 19. Bh3 d5 "
                 "20. Qf4+ Ka7 21. Rhe1 d4 22. Nd5 Nbxd5 23. exd5 Qd6 24. Rxd4 cxd4 25. Re7+ Kb6 "
                 "26. Qxd4+ Kxa5 27. b4+ Ka4 28. Qc3 Qxd5 29. Ra7 Bb7 30. Rxb7 Qc4 31. Qxf6 Kxa3 "
                 "32. Qxa6+ Kxb4 33. c3+ Kxc3 34. Qa1+ Kd2 35. Qb2+ Kd1 36. Bf1 Rd2 37. Rd7 Rxd7 "
                 "38. Bxc4 bxc4 39. Qxh8 Rd3 40. Qa8 c3 41. Qa4+ Ke1 42. f4 f5 43. Kc1 Rd2 44. Qa7",
    },
    {
        "id": "deepblue-kasparov-1997",
        "white": "Deep Blue",
        "black": "Garry Kasparov",
        "event": "IBM Man vs Machine, New York",
        "year": 1997,
        "result": "1-0",
        "nickname": "Machine Beats Champion",
        "description": "The decisive Game 6: Deep Blue's knight sacrifice on e6 "
                       "becomes the first match win by a computer over a world champion.",
        "moves": "1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Nd7 5. Ng5 Ngf6 6. Bd3 e6 "
                 "7. N1f3 h6 8. Nxe6 Qe7 9. O-O fxe6 10. Bg6+ Kd8 11. Bf4 b5 12. a4 Bb7 "
                 "13. Re1 Nd5 14. Bg3 Kc8 15. axb5 cxb5 16. Qd3 Bc6 17. Bf5 exf5 18. Rxe7 Bxe7 "
                 "19. c4",
    },
    {
        "id": "fischer-spassky-1972-g6",
        "white": "Robert James Fischer",
        "black": "Boris Spassky",
        "event": "World Championship, Reykjavik",
        "year": 1972,
        "result": "1-0",
        "nickname": "Fischer's Queen's Gambit",
        "description": "Game 6 of the 1972 match — Fischer plays 1.c4 and produces a "
                       "model positional game Spassky reportedly applauded.",
        "moves": "1. c4 e6 2. Nf3 d5 3. d4 Nf6 4. Nc3 Be7 5. Bg5 O-O 6. e3 h6 7. Bh4 b6 "
                 "8. cxd5 Nxd5 9. Bxe7 Qxe7 10. Nxd5 exd5 11. Rc1 Be6 12. Qa4 c5 13. Qa3 Rc8 "
                 "14. Bb5 a6 15. dxc5 bxc5 16. O-O Ra7 17. Be2 Nd7 18. Nd4 Qf8 19. Nxe6 fxe6 "
                 "20. e4 d4 21. f4 Qe7 22. e5 Rb8 23. Bc4 Kh8 24. Qh3 Nf8 25. b3 a5 26. f5 exf5 "
                 "27. Rxf5 Nh7 28. Rcf1 Qd8 29. Qg3 Re7 30. h4 Rbb7 31. e6 Rbc7 32. Qe5 Qe8 "
                 "33. a4 Qd8 34. R1f2 Qe8 35. R2f3 Qd8 36. Bd3 Qe8 37. Qe4 Nf6 38. Rxf6 gxf6 "
                 "39. Rxf6 Kg8 40. Bc4 Kh8 41. Qf4",
    },
    {
        "id": "rotlewi-rubinstein-1907",
        "white": "Georg Rotlewi",
        "black": "Akiba Rubinstein",
        "event": "Lodz",
        "year": 1907,
        "result": "0-1",
        "nickname": "Rubinstein's Immortal",
        "description": "Rubinstein's masterpiece ends with a cascade of sacrifices "
                       "(...Rxc3, ...Rd2, ...Bxe4+, ...Rh3) that cannot be met.",
        "moves": "1. d4 d5 2. Nf3 e6 3. e3 c5 4. c4 Nc6 5. Nc3 Nf6 6. dxc5 Bxc5 7. a3 a6 "
                 "8. b4 Bd6 9. Bb2 O-O 10. Qd2 Qe7 11. Bd3 dxc4 12. Bxc4 b5 13. Bd3 Rd8 "
                 "14. Qe2 Bb7 15. O-O Ne5 16. Nxe5 Bxe5 17. f4 Bc7 18. e4 Rac8 19. e5 Bb6+ "
                 "20. Kh1 Ng4 21. Be4 Qh4 22. g3 Rxc3 23. gxh4 Rd2 24. Qxd2 Bxe4+ 25. Qg2 Rh3",
    },
    {
        "id": "botvinnik-capablanca-1938",
        "white": "Mikhail Botvinnik",
        "black": "Jose Raul Capablanca",
        "event": "AVRO, Netherlands",
        "year": 1938,
        "result": "1-0",
        "nickname": "Botvinnik's Combination",
        "description": "Botvinnik's celebrated 30.Ba3!! and 30...Qxa3 31.Nh5+!! "
                       "deflection sequence overwhelms a legend.",
        "moves": "1. d4 Nf6 2. c4 e6 3. Nc3 Bb4 4. e3 d5 5. a3 Bxc3+ 6. bxc3 c5 7. cxd5 exd5 "
                 "8. Bd3 O-O 9. Ne2 b6 10. O-O Ba6 11. Bxa6 Nxa6 12. Bb2 Qd7 13. a4 Rfe8 "
                 "14. Qd3 c4 15. Qc2 Nb8 16. Rae1 Nc6 17. Ng3 Na5 18. f3 Nb3 19. e4 Qxa4 "
                 "20. e5 Nd7 21. Qf2 g6 22. f4 f5 23. exf6 Nxf6 24. f5 Rxe1 25. Rxe1 Re8 "
                 "26. Re6 Rxe6 27. fxe6 Kg7 28. Qf4 Qe8 29. Qe5 Qe7 30. Ba3 Qxa3 31. Nh5+ gxh5 "
                 "32. Qg5+ Kf8 33. Qxf6+ Kg8 34. e7 Qc1+ 35. Kf2 Qc2+ 36. Kg3 Qd3+ 37. Kh4 Qe4+ "
                 "38. Kxh5 Qe2+ 39. Kh4 Qe4+ 40. g4 Qe1+ 41. Kh5",
    },
    {
        "id": "steinitz-bardeleben-1895",
        "white": "Wilhelm Steinitz",
        "black": "Curt von Bardeleben",
        "event": "Hastings",
        "year": 1895,
        "result": "1-0",
        "nickname": "Steinitz's Brilliancy",
        "description": "Steinitz keeps his rook en prise for moves on end; von "
                       "Bardeleben quietly left the hall rather than resign.",
        "moves": "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ "
                 "7. Nc3 d5 8. exd5 Nxd5 9. O-O Be6 10. Bg5 Be7 11. Bxd5 Bxd5 12. Nxd5 Qxd5 "
                 "13. Bxe7 Nxe7 14. Re1 f6 15. Qe2 Qd7 16. Rac1 c6 17. d5 cxd5 18. Nd4 Kf7 "
                 "19. Ne6 Rhc8 20. Qg4 g6 21. Ng5+ Ke8 22. Rxe7+ Kf8 23. Rf7+ Kg8 24. Rg7+ Kh8 "
                 "25. Rxh7+",
    },
    {
        "id": "short-timman-1991",
        "white": "Nigel Short",
        "black": "Jan Timman",
        "event": "Tilburg",
        "year": 1991,
        "result": "1-0",
        "nickname": "The King Walk",
        "description": "Short marches his king up the board (Kg1-h6!) to set up an "
                       "unstoppable mate — one of the most famous king walks ever.",
        "moves": "1. e4 Nf6 2. e5 Nd5 3. d4 d6 4. Nf3 g6 5. Bc4 Nb6 6. Bb3 Bg7 7. Qe2 Nc6 "
                 "8. O-O O-O 9. h3 a5 10. a4 dxe5 11. dxe5 Nd4 12. Nxd4 Qxd4 13. Re1 e6 "
                 "14. Nd2 Nd5 15. Nf3 Qc5 16. Qe4 Qb4 17. Bc4 Nb6 18. b3 Nxc4 19. bxc4 Re8 "
                 "20. Rd1 Qc5 21. Qh4 b6 22. Be3 Qc6 23. Bh6 Bh8 24. Rd8 Bb7 25. Rad1 Bg7 "
                 "26. R8d7 Rf8 27. Bxg7 Kxg7 28. R1d4 Rae8 29. Qf6+ Kg8 30. h4 h5 31. Kh2 Rc8 "
                 "32. Kg3 Rce8 33. Kf4 Bc8 34. Kg5",
    },
    {
        "id": "byrne-fischer-1963",
        "white": "Robert Byrne",
        "black": "Robert James Fischer",
        "event": "US Championship, New York",
        "year": 1963,
        "result": "0-1",
        "nickname": "Fischer's Other Brilliancy",
        "description": "Byrne resigned in a position that looked fine to spectators — "
                       "only the grandmasters saw Fischer's crushing finish.",
        "moves": "1. d4 Nf6 2. c4 g6 3. g3 c6 4. Bg2 d5 5. cxd5 cxd5 6. Nc3 Bg7 7. e3 O-O "
                 "8. Nge2 Nc6 9. O-O b6 10. b3 Ba6 11. Ba3 Re8 12. Qd2 e5 13. dxe5 Nxe5 "
                 "14. Rfd1 Nd3 15. Qc2 Nxf2 16. Kxf2 Ng4+ 17. Kg1 Nxe3 18. Qd2 Nxg2 19. Kxg2 d4 "
                 "20. Nxd4 Bb7+ 21. Kf1 Qd7",
    },
    {
        "id": "aronian-anand-2013",
        "white": "Levon Aronian",
        "black": "Viswanathan Anand",
        "event": "Tata Steel, Wijk aan Zee",
        "year": 2013,
        "result": "0-1",
        "nickname": "Anand's Modern Brilliancy",
        "description": "Anand's ...Nde5!! and the quiet ...Be3! produce a 21st-century "
                       "classic, hailed as one of the best games of the decade.",
        "moves": "1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 e6 5. e3 Nbd7 6. Bd3 dxc4 7. Bxc4 b5 "
                 "8. Bd3 Bd6 9. O-O O-O 10. Qc2 Bb7 11. a3 Rc8 12. Ng5 c5 13. Nxh7 Ng4 "
                 "14. f4 cxd4 15. exd4 Bc5 16. Be2 Nde5 17. Bxg4 Bxd4+ 18. Kh1 Nxg4 19. Nxf8 f5 "
                 "20. Ng6 Qf6 21. h3 Qxg6 22. Qe2 Qh5 23. Qd3 Be3",
    },
    {
        "id": "levitsky-marshall-1912",
        "white": "Stepan Levitsky",
        "black": "Frank Marshall",
        "event": "Breslau",
        "year": 1912,
        "result": "0-1",
        "nickname": "The Gold Coins Game",
        "description": "Marshall's ...Qg3!! — placing the queen where three pieces "
                       "can take it — legendarily drew a shower of gold coins.",
        "moves": "1. d4 e6 2. e4 d5 3. Nc3 c5 4. Nf3 Nc6 5. exd5 exd5 6. Be2 Nf6 7. O-O Be7 "
                 "8. Bg5 O-O 9. dxc5 Be6 10. Nd4 Bxc5 11. Nxe6 fxe6 12. Bg4 Qd6 13. Bh3 Rae8 "
                 "14. Qd2 Bb4 15. Bxf6 Rxf6 16. Rad1 Qc5 17. Qe2 Bxc3 18. bxc3 Qxc3 19. Rxd5 Nd4 "
                 "20. Qh5 Ref8 21. Re5 Rh6 22. Qg5 Rxh3 23. Rc5 Qg3",
    },
    {
        "id": "spassky-bronstein-1960",
        "white": "Boris Spassky",
        "black": "David Bronstein",
        "event": "USSR Championship, Leningrad",
        "year": 1960,
        "result": "1-0",
        "nickname": "The Bond Game",
        "description": "A King's Gambit fireworks display later recreated on screen in "
                       "'From Russia with Love'.",
        "moves": "1. e4 e5 2. f4 exf4 3. Nf3 d5 4. exd5 Bd6 5. Nc3 Ne7 6. d4 O-O 7. Bd3 Nd7 "
                 "8. O-O h6 9. Ne4 Nxd5 10. c4 Ne3 11. Bxe3 fxe3 12. c5 Be7 13. Bc2 Re8 "
                 "14. Qd3 e2 15. Nd6 Nf8 16. Nxf7 exf1=Q+ 17. Rxf1 Bf5 18. Qxf5 Qd7 19. Qf4 Bf6 "
                 "20. N3e5 Qe7 21. Bb3 Bxe5 22. Nxe5+ Kh7 23. Qe4+",
    },
    {
        "id": "karpov-kasparov-1985-g16",
        "white": "Anatoly Karpov",
        "black": "Garry Kasparov",
        "event": "World Championship, Moscow",
        "year": 1985,
        "result": "0-1",
        "nickname": "The Octopus Knight",
        "description": "Kasparov's knight lands on d3 and strangles White's position — "
                       "a defining game of his rise to the title.",
        "moves": "1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nb5 d6 6. c4 Nf6 7. N1c3 a6 "
                 "8. Na3 d5 9. cxd5 exd5 10. exd5 Nb4 11. Be2 Bc5 12. O-O O-O 13. Bf3 Bf5 "
                 "14. Bg5 Re8 15. Qd2 b5 16. Rad1 Nd3 17. Nab1 h6 18. Bh4 b4 19. Na4 Bd6 "
                 "20. Bg3 Rc8 21. b3 g5 22. Bxd6 Qxd6 23. g3 Nd7 24. Bg2 Qf6 25. a3 a5 "
                 "26. axb4 axb4 27. Qa2 Bg6 28. d6 g4 29. Qd2 Kg7 30. f3 Qxd6 31. fxg4 Qd4+ "
                 "32. Kh1 Nf6 33. Rf4 Ne4 34. Qxd3 Nf2+ 35. Rxf2 Bxd3 36. Rfd2 Qe3 37. Rxd3 Rc1 "
                 "38. Nb2 Qf2 39. Nd2 Rxd1+ 40. Nxd1 Re1+",
    },
    {
        "id": "paulsen-morphy-1857",
        "white": "Louis Paulsen",
        "black": "Paul Morphy",
        "event": "First American Chess Congress, New York",
        "year": 1857,
        "result": "0-1",
        "nickname": "Morphy's Queen Sacrifice",
        "description": "Morphy's thunderbolt ...Qxf3!! tears open the white king and "
                       "is one of the most famous combinations of the romantic era.",
        "moves": "1. e4 e5 2. Nf3 Nc6 3. Nc3 Nf6 4. Bb5 Bc5 5. O-O O-O 6. Nxe5 Re8 7. Nxc6 dxc6 "
                 "8. Bc4 b5 9. Be2 Nxe4 10. Nxe4 Rxe4 11. Bf3 Re6 12. c3 Qd3 13. b4 Bb6 14. a4 bxa4 "
                 "15. Qxa4 Bd7 16. Ra2 Rae8 17. Qa6 Qxf3 18. gxf3 Rg6+ 19. Kh1 Bh3 20. Rd1 Bg2+ "
                 "21. Kg1 Bxf3+ 22. Kf1 Bg2+ 23. Kg1 Bh3+ 24. Kh1 Bxf2 25. Qf1 Bxf1 26. Rxf1 Re2 "
                 "27. Ra1 Rh6 28. d4 Be3",
    },
    {
        "id": "reti-bogoljubov-1924",
        "white": "Richard Reti",
        "black": "Efim Bogoljubov",
        "event": "New York",
        "year": 1924,
        "result": "1-0",
        "nickname": "Reti's Bishop Finish",
        "description": "Reti's hypermodern strategy culminates in the elegant 24.Bf7+ "
                       "and 25.Be8! winning material by force.",
        "moves": "1. Nf3 d5 2. c4 e6 3. g3 Nf6 4. Bg2 Bd6 5. O-O O-O 6. b3 Re8 7. Bb2 Nbd7 "
                 "8. d4 c6 9. Nbd2 Ne4 10. Nxe4 dxe4 11. Ne5 f5 12. f3 exf3 13. Bxf3 Qc7 "
                 "14. Nxd7 Bxd7 15. e4 e5 16. c5 Bf8 17. Qc2 exd4 18. exf5 Rad8 19. Bh5 Re5 "
                 "20. Bxd4 Rxf5 21. Rxf5 Bxf5 22. Qxf5 Rxd4 23. Rf1 Rd8 24. Bf7+ Kh8 25. Be8",
    },
    {
        "id": "lasker-bauer-1889",
        "white": "Emanuel Lasker",
        "black": "Johann Bauer",
        "event": "Amsterdam",
        "year": 1889,
        "result": "1-0",
        "nickname": "The Double Bishop Sacrifice",
        "description": "The original double-bishop sacrifice (Bxh7+ then Bxg7) — a "
                       "pattern still taught to attackers over a century later.",
        "moves": "1. f4 d5 2. e3 Nf6 3. b3 e6 4. Bb2 Be7 5. Bd3 b6 6. Nf3 Bb7 7. Nc3 Nbd7 "
                 "8. O-O O-O 9. Ne2 c5 10. Ng3 Qc7 11. Ne5 Nxe5 12. Bxe5 Qc6 13. Qe2 a6 "
                 "14. Nh5 Nxh5 15. Bxh7+ Kxh7 16. Qxh5+ Kg8 17. Bxg7 Kxg7 18. Qg4+ Kh7 19. Rf3 e5 "
                 "20. Rh3+ Qh6 21. Rxh6+ Kxh6 22. Qd7 Bf6 23. Qxb7 Kg7 24. Rf1 Rab8 25. Qd7 Rfd8 "
                 "26. Qg4+ Kf8 27. fxe5 Bg7 28. e6 Rb7 29. Qg6 f6 30. Rxf6+ Bxf6 31. Qxf6+ Ke8 "
                 "32. Qh8+ Ke7 33. Qg7+ Kxe6 34. Qxb7",
    },
    {
        "id": "fischer-myagmarsuren-1967",
        "white": "Robert James Fischer",
        "black": "Lhamsuren Myagmarsuren",
        "event": "Interzonal, Sousse",
        "year": 1967,
        "result": "1-0",
        "nickname": "Fischer's King's Indian Attack",
        "description": "A textbook King's Indian Attack kingside assault ending with the "
                       "crisp 31.Qxh7+!! and a forced mate.",
        "moves": "1. e4 e6 2. d3 d5 3. Nd2 Nf6 4. g3 c5 5. Bg2 Nc6 6. Ngf3 Be7 7. O-O O-O "
                 "8. e5 Nd7 9. Re1 b5 10. Nf1 b4 11. h4 a5 12. Bf4 a4 13. a3 bxa3 14. bxa3 Na5 "
                 "15. Ne3 Ba6 16. Bh3 d4 17. Nf1 Nb6 18. Ng5 Nd5 19. Bd2 Bxg5 20. Bxg5 Qd7 "
                 "21. Qh5 Rfc8 22. Nd2 Nc3 23. Bf6 Qe8 24. Ne4 g6 25. Qg5 Nxe4 26. Rxe4 c4 "
                 "27. h5 cxd3 28. Rh4 Ra7 29. Bg2 dxc2 30. Qh6 Qf8 31. Qxh7+ Kxh7 32. hxg6+ Kxg6 "
                 "33. Be4#",
    },
]
