"""
Summary Repository

Handles insert of option chain summary
"""

from database.db_connection import DatabaseConnection


class SummaryRepository:

    @staticmethod
    def insert_summary(
        symbol: str,
        snapshot_time,
        spot_price: float,
        atm_strike: float,
        total_ce_oi: float,
        total_pe_oi: float,
        pcr: float,
        resistance: float,
        support: float,
        max_pain: float,
        structure: str,
        trap_signal: str
    ) -> None:

        insert_query = """
        INSERT INTO option_chain_summary (
            symbol,
            snapshot_time,
            spot_price,
            atm_strike,
            total_ce_oi,
            total_pe_oi,
            pcr,
            resistance,
            support,
            max_pain,
            structure,
            trap_signal
        )
        VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        """

        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                insert_query,
                (
                    symbol,
                    snapshot_time,
                    spot_price,
                    atm_strike,
                    total_ce_oi,
                    total_pe_oi,
                    pcr,
                    resistance,
                    support,
                    max_pain,
                    structure,
                    trap_signal
                )
            )
            conn.commit()

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Summary insert failed: {e}")

        finally:
            cursor.close()
            DatabaseConnection.release_connection(conn)
